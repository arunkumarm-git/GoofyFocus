import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? ""
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? ""

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response("ok", {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    })
  }

  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 })
  }

  try {
    const rawBody = await req.text()
    const params = new URLSearchParams(rawBody)

    // 1. Determine validation URL based on the test_ipn flag
    const isSandbox = params.get("test_ipn") === "1"
    const validationUrl = isSandbox 
      ? "https://ipnpb.sandbox.paypal.com/cgi-bin/webscr"
      : "https://ipnpb.paypal.com/cgi-bin/webscr"

    console.log(`[PayPal Webhook] Received IPN request. Sandbox: ${isSandbox}. Validating with PayPal...`)

    // 2. Post verification message back to PayPal for verification
    const verificationBody = "cmd=_notify-validate&" + rawBody
    const verifyRes = await fetch(validationUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: verificationBody,
    })

    const verificationResult = await verifyRes.text()
    console.log(`[PayPal Webhook] Verification response from PayPal: ${verificationResult}`)

    if (verificationResult !== "VERIFIED") {
      console.error("[PayPal Webhook] IPN Verification failed.")
      return new Response("IPN Verification Failed", { status: 400 })
    }

    // 3. Process the verified payment event
    const paymentStatus = params.get("payment_status")
    const customUserId = params.get("custom")
    const payerEmail = params.get("payer_email")
    const txnId = params.get("txn_id")

    console.log(`[PayPal Webhook] Verified transaction: status=${paymentStatus}, customUserId=${customUserId}, payerEmail=${payerEmail}, txnId=${txnId}`)

    // 4. Update the user's Pro status in the Supabase database
    // "Completed" marks the payment as successful.
    // "Refunded", "Reversed", or "Denied" cancels or reverts the Pro status.
    const isCompleted = paymentStatus === "Completed"
    const isReversed = ["Refunded", "Reversed", "Denied", "Canceled_Reversal", "Failed"].includes(paymentStatus ?? "")

    if (isCompleted || isReversed) {
      const isPro = isCompleted
      let updated = false

      // Primary match: by custom user ID (google_sub) passed during checkout
      if (customUserId) {
        console.log(`[PayPal Webhook] Attempting update for user_id (google_sub) ${customUserId} to is_pro = ${isPro}`)
        const { error } = await supabase
          .from("users")
          .update({ is_pro: isPro })
          .eq("google_sub", customUserId)

        if (error) {
          console.error(`[PayPal Webhook] Error updating by google_sub: ${error.message}`)
        } else {
          updated = true
        }
      }

      // Secondary match fallback: by payer email
      if (!updated && payerEmail) {
        console.log(`[PayPal Webhook] Fallback: Attempting update for email ${payerEmail} to is_pro = ${isPro}`)
        const { error } = await supabase
          .from("users")
          .update({ is_pro: isPro })
          .eq("email", payerEmail)

        if (error) {
          console.error(`[PayPal Webhook] Error updating by email: ${error.message}`)
        } else {
          updated = true
        }
      }

      if (updated) {
        console.log(`[PayPal Webhook] Successfully updated user Pro status to ${isPro}`)
      } else {
        console.warn(`[PayPal Webhook] User not found or update skipped for user_id=${customUserId}, email=${payerEmail}`)
      }
    } else {
      console.log(`[PayPal Webhook] Ignored payment_status: ${paymentStatus}`)
    }

    return new Response("OK", { status: 200 })
  } catch (err: any) {
    console.error(`[PayPal Webhook] Error processing webhook: ${err.message}`)
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    })
  }
})
