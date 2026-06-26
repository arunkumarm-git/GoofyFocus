package com.arunkumar.goofyfocus.billing

import android.app.Activity
import android.content.Context
import com.android.billingclient.api.*
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class BillingManager(
    private val context: Context,
    private val coroutineScope: CoroutineScope,
    private val onPurchaseCompleted: (productId: String) -> Unit
) : PurchasesUpdatedListener {

    private val billingClient = BillingClient.newBuilder(context)
        .setListener(this)
        .enablePendingPurchases()
        .build()

    private var retryCount = 0
    private val maxRetries = 3

    init {
        startConnection()
    }

    private fun startConnection(onComplete: ((Boolean) -> Unit)? = null) {
        android.util.Log.d("BillingManager", "Starting billing client connection...")
        billingClient.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(billingResult: BillingResult) {
                if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                    android.util.Log.i("BillingManager", "Billing client setup finished successfully.")
                    retryCount = 0
                    queryActivePurchases()
                    onComplete?.invoke(true)
                } else {
                    android.util.Log.e("BillingManager", "Billing setup failed: Code ${billingResult.responseCode}, Msg: ${billingResult.debugMessage}")
                    retryConnection(onComplete)
                }
            }
            override fun onBillingServiceDisconnected() {
                android.util.Log.w("BillingManager", "Billing service disconnected.")
                retryConnection(onComplete)
            }
        })
    }

    private fun retryConnection(onComplete: ((Boolean) -> Unit)? = null) {
        if (retryCount < maxRetries) {
            retryCount++
            val delayMillis = 3000L * retryCount
            android.util.Log.d("BillingManager", "Retrying billing connection (attempt $retryCount/$maxRetries) in ${delayMillis}ms")
            coroutineScope.launch {
                kotlinx.coroutines.delay(delayMillis)
                startConnection(onComplete)
            }
        } else {
            android.util.Log.e("BillingManager", "Max billing connection retries reached.")
            onComplete?.invoke(false)
        }
    }

    fun launchBillingFlow(activity: Activity, productId: String, productType: String) {
        android.util.Log.d("BillingManager", "launchBillingFlow called for product: $productId ($productType)")
        
        if (!billingClient.isReady) {
            android.util.Log.w("BillingManager", "BillingClient is not ready. Attempting to reconnect...")
            activity.runOnUiThread {
                android.widget.Toast.makeText(context, "Initializing Google Play Billing. Please try again in a moment.", android.widget.Toast.LENGTH_SHORT).show()
            }
            startConnection { success ->
                if (success) {
                    launchBillingFlow(activity, productId, productType)
                } else {
                    activity.runOnUiThread {
                        android.widget.Toast.makeText(activity, "Failed to connect to Google Play Billing. Please check your network connection.", android.widget.Toast.LENGTH_LONG).show()
                    }
                }
            }
            return
        }

        val productList = listOf(
            QueryProductDetailsParams.Product.newBuilder()
                .setProductId(productId)
                .setProductType(productType)
                .build()
        )

        val params = QueryProductDetailsParams.newBuilder()
            .setProductList(productList)
            .build()

        android.util.Log.d("BillingManager", "Querying product details for $productId...")
        billingClient.queryProductDetailsAsync(params) { billingResult, productDetailsList ->
            val responseCode = billingResult.responseCode
            if (responseCode == BillingClient.BillingResponseCode.OK) {
                if (productDetailsList.isNotEmpty()) {
                    val productDetails = productDetailsList[0]
                    android.util.Log.d("BillingManager", "Product details queried successfully: ${productDetails.name}")
                    
                    val productDetailsParamsList = listOf(
                        BillingFlowParams.ProductDetailsParams.newBuilder()
                            .setProductDetails(productDetails)
                            .apply {
                                if (productType == BillingClient.ProductType.SUBS) {
                                    val offerToken = productDetails.subscriptionOfferDetails?.firstOrNull()?.offerToken
                                    if (offerToken != null) {
                                        setOfferToken(offerToken)
                                    } else {
                                        android.util.Log.e("BillingManager", "No subscription offer details or offer token found for product: $productId")
                                        activity.runOnUiThread {
                                            android.widget.Toast.makeText(activity, "Error: No active offer found for this subscription in Play Console.", android.widget.Toast.LENGTH_LONG).show()
                                        }
                                        return@queryProductDetailsAsync
                                    }
                                }
                            }
                            .build()
                    )

                    val billingFlowParams = BillingFlowParams.newBuilder()
                        .setProductDetailsParamsList(productDetailsParamsList)
                        .build()

                    android.util.Log.i("BillingManager", "Launching Google Play Billing flow for $productId")
                    val flowResult = billingClient.launchBillingFlow(activity, billingFlowParams)
                    if (flowResult.responseCode != BillingClient.BillingResponseCode.OK) {
                        val errorMsg = "Billing flow launch failed: Code ${flowResult.responseCode}, Msg: ${flowResult.debugMessage}"
                        android.util.Log.e("BillingManager", errorMsg)
                        activity.runOnUiThread {
                            android.widget.Toast.makeText(activity, errorMsg, android.widget.Toast.LENGTH_LONG).show()
                        }
                    }
                } else {
                    val errorMsg = "Product '$productId' was not found in the Google Play Store configuration."
                    android.util.Log.e("BillingManager", errorMsg)
                    activity.runOnUiThread {
                        android.widget.Toast.makeText(activity, errorMsg, android.widget.Toast.LENGTH_LONG).show()
                    }
                }
            } else {
                val errorMsg = "Failed to retrieve subscription details: Code $responseCode (${billingResult.debugMessage})"
                android.util.Log.e("BillingManager", errorMsg)
                activity.runOnUiThread {
                    android.widget.Toast.makeText(activity, errorMsg, android.widget.Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    override fun onPurchasesUpdated(billingResult: BillingResult, purchases: List<Purchase>?) {
        val responseCode = billingResult.responseCode
        android.util.Log.d("BillingManager", "onPurchasesUpdated: Code $responseCode, Purchases Count: ${purchases?.size ?: 0}")
        if (responseCode == BillingClient.BillingResponseCode.OK && purchases != null) {
            for (purchase in purchases) {
                handlePurchase(purchase)
            }
        } else if (responseCode == BillingClient.BillingResponseCode.USER_CANCELED) {
            android.util.Log.i("BillingManager", "Billing purchase flow canceled by the user.")
        } else {
            android.util.Log.w("BillingManager", "Purchases updated with failure: Code $responseCode, Msg: ${billingResult.debugMessage}")
        }
    }

    private fun handlePurchase(purchase: Purchase) {
        android.util.Log.d("BillingManager", "handlePurchase called for: ${purchase.orderId}, State: ${purchase.purchaseState}")
        if (purchase.purchaseState == Purchase.PurchaseState.PURCHASED) {
            if (!purchase.isAcknowledged) {
                android.util.Log.d("BillingManager", "Acknowledging purchase: ${purchase.purchaseToken}")
                val acknowledgePurchaseParams = AcknowledgePurchaseParams.newBuilder()
                    .setPurchaseToken(purchase.purchaseToken)
                    .build()
                
                billingClient.acknowledgePurchase(acknowledgePurchaseParams) { billingResult ->
                    if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                        android.util.Log.i("BillingManager", "Purchase successfully acknowledged.")
                        coroutineScope.launch {
                            withContext(Dispatchers.Main) {
                                onPurchaseCompleted(purchase.products.firstOrNull() ?: "")
                            }
                        }
                    } else {
                        android.util.Log.e("BillingManager", "Failed to acknowledge purchase: Code ${billingResult.responseCode}, Msg: ${billingResult.debugMessage}")
                    }
                }
            } else {
                android.util.Log.d("BillingManager", "Purchase already acknowledged, updating status.")
                coroutineScope.launch {
                    withContext(Dispatchers.Main) {
                        onPurchaseCompleted(purchase.products.firstOrNull() ?: "")
                    }
                }
            }
        } else if (purchase.purchaseState == Purchase.PurchaseState.PENDING) {
            android.util.Log.d("BillingManager", "Purchase is pending payment.")
        }
    }

    fun queryActivePurchases() {
        val params = QueryPurchasesParams.newBuilder()
            .setProductType(BillingClient.ProductType.SUBS)
            .build()

        billingClient.queryPurchasesAsync(params) { billingResult, purchasesList ->
            if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                for (purchase in purchasesList) {
                    if (purchase.purchaseState == Purchase.PurchaseState.PURCHASED) {
                        handlePurchase(purchase)
                    }
                }
            }
        }
    }
}
