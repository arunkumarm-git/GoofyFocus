package com.arunkumar.goofyfocus.ui

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.border
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.arunkumar.goofyfocus.TimerService
import com.arunkumar.goofyfocus.MainActivity
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.Spring
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import kotlinx.coroutines.delay
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.auth.api.signin.GoogleSignInClient
import com.arunkumar.goofyfocus.billing.BillingManager
import com.android.billingclient.api.BillingClient
import android.app.Activity

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    var isVisible by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        isVisible = true
    }

    // Auto-save feedback pulse indicators (Jakob's Law UI feedback)
    var saveTrigger by remember { mutableStateOf(0) }
    val saveIndicatorColor by animateColorAsState(
        targetValue = if (saveTrigger > 0) Color(0xFF34D399) else Color(0x66FFFFFF),
        animationSpec = tween(300),
        label = "save_color"
    )
    val onSettingsSaved = {
        coroutineScope.launch {
            saveTrigger++
            delay(1200)
            saveTrigger--
        }
    }

    val handleBack = {
        coroutineScope.launch {
            isVisible = false
            delay(250)
            onBack()
        }
    }

    // Load active settings states
    val customGifUri by TimerService.customGifUri.collectAsState()
    val mascotType by TimerService.mascotType.collectAsState()
    val isPro by TimerService.isPro.collectAsState()
    val proExpiryTime by TimerService.proExpiryTime.collectAsState()
    val googleUserSub by TimerService.googleUserSub.collectAsState()
    val googleUserEmail by TimerService.googleUserEmail.collectAsState()
    val googleUserName by TimerService.googleUserName.collectAsState()
    val googleUserPicture by TimerService.googleUserPicture.collectAsState()
    val premiumDuration by TimerService.premiumDuration.collectAsState()
    val premiumHours by TimerService.premiumHours.collectAsState()

    var selectedOption by remember { mutableStateOf("1 Month") }
    var showPlayBillingSheet by remember { mutableStateOf(false) }
    var isProcessingPayment by remember { mutableStateOf(false) }
    var isCheckingProOnLogin by remember { mutableStateOf(false) }
    var pendingPurchaseOnLogin by remember { mutableStateOf(false) }
    
    val billingManager = remember {
        BillingManager(context, coroutineScope) { productId ->
            val addedHours = when (productId) {
                "goofyfocus_1month" -> 744 // 31 days
                "goofyfocus_6months" -> 4464
                "goofyfocus_1year" -> 8928
                else -> 0
            }
            if (addedHours > 0) {
                coroutineScope.launch {
                    val sub = TimerService.googleUserSub.value ?: "guest"
                    val email = TimerService.googleUserEmail.value ?: "guest"
                    val name = TimerService.googleUserName.value
                    val pic = TimerService.googleUserPicture.value
                    val newHours = TimerService.premiumHours.value + addedHours
                    val success = syncUserToSupabase(sub, email, name, pic, true, newHours)
                    if (success) {
                        TimerService.signInUserWithHours(context, sub, email, name, pic, newHours, System.currentTimeMillis())
                        com.arunkumar.goofyfocus.audio.SoundSynthesizer.playSuccessSound()
                        android.widget.Toast.makeText(context, "Subscription activated & synced to cloud! 🎉", android.widget.Toast.LENGTH_LONG).show()
                    } else {
                        android.widget.Toast.makeText(context, "Cloud sync failed. Local premium activated.", android.widget.Toast.LENGTH_LONG).show()
                        TimerService.signInUserWithHours(context, sub, email, name, pic, newHours, System.currentTimeMillis())
                    }
                }
            }
        }
    }

    val gso = remember {
        GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestIdToken(context.getString(com.arunkumar.goofyfocus.R.string.default_web_client_id))
            .requestEmail()
            .requestProfile()
            .build()
    }
    val googleSignInClient = remember { GoogleSignIn.getClient(context, gso) }

    val googleSignInLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult()
    ) { result ->
        val task = GoogleSignIn.getSignedInAccountFromIntent(result.data)
        try {
            val account = task.getResult(com.google.android.gms.common.api.ApiException::class.java)
            if (account != null) {
                val email = account.email ?: ""
                val name = account.displayName ?: ""
                val sub = account.id ?: ""
                val picture = account.photoUrl?.toString() ?: ""
                
                coroutineScope.launch {
                    isCheckingProOnLogin = true
                    val existingPair = checkProStatusFromSupabase(email)
                    isCheckingProOnLogin = false
                    if (existingPair != null && existingPair.first > 0) {
                        TimerService.signInUserWithHours(context, sub, email, name, picture, existingPair.first, existingPair.second)
                        syncUserToSupabase(sub, email, name, picture, true, existingPair.first)
                        com.arunkumar.goofyfocus.audio.SoundSynthesizer.playSuccessSound()
                        android.widget.Toast.makeText(context, "Welcome back! Premium restored. 🎉", android.widget.Toast.LENGTH_LONG).show()
                    } else {
                        TimerService.signInUser(context, sub, email, name, picture, null)
                        syncUserToSupabase(sub, email, name, picture, false, 0)
                        if (pendingPurchaseOnLogin) {
                            showPlayBillingSheet = true
                        } else {
                            android.widget.Toast.makeText(context, "Logged in successfully! 👤", android.widget.Toast.LENGTH_SHORT).show()
                        }
                    }
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
            val apiException = e as? com.google.android.gms.common.api.ApiException
            val statusCode = apiException?.statusCode ?: -1
            val errorMsg = when (statusCode) {
                10 -> "Developer Error (Status 10). Ensure your debug SHA-1 signature is registered in Google Cloud Console."
                12500 -> "Sign-in configuration mismatch (Status 12500)."
                else -> "Google Sign-in failed (Status $statusCode): ${e.message}"
            }
            android.widget.Toast.makeText(context, errorMsg, android.widget.Toast.LENGTH_LONG).show()
        }
    }
    var showDeleteAccountDialog by remember { mutableStateOf(false) }

    var remainingTimeText by remember { mutableStateOf("") }
    LaunchedEffect(proExpiryTime) {
        if (proExpiryTime > System.currentTimeMillis()) {
            while (proExpiryTime > System.currentTimeMillis()) {
                val diff = proExpiryTime - System.currentTimeMillis()
                val hours = diff / (60 * 60 * 1000)
                val mins = (diff % (60 * 60 * 1000)) / (60 * 1000)
                remainingTimeText = String.format("%02dh %02dm remaining", hours, mins)
                delay(60000)
            }
        }
        val prefs = context.getSharedPreferences("GoofyFocusPrefs", Context.MODE_PRIVATE)
        val permanentPro = prefs.getBoolean("IS_PRO", false)
        if (!permanentPro && proExpiryTime > 0L && proExpiryTime <= System.currentTimeMillis()) {
            TimerService.isPro.value = false
            TimerService.workSecs.value = 25 * 60
            TimerService.shortBreakSecs.value = 5 * 60
            TimerService.longBreakSecs.value = 10 * 60
            TimerService.sessionsPerCycle.value = 4
        }
    }

    val currentWorkSecs by TimerService.workSecs.collectAsState()
    val currentShortSecs by TimerService.shortBreakSecs.collectAsState()
    val currentLongSecs by TimerService.longBreakSecs.collectAsState()
    val currentSessionsPerCycle by TimerService.sessionsPerCycle.collectAsState()
    val currentBreakFlow by TimerService.breakFlow.collectAsState()

    var workMins by remember { mutableFloatStateOf((currentWorkSecs / 60).toFloat()) }
    var shortMins by remember { mutableFloatStateOf((currentShortSecs / 60).toFloat()) }
    var longMins by remember { mutableFloatStateOf((currentLongSecs / 60).toFloat()) }
    var sessionsPerCycle by remember { mutableFloatStateOf(currentSessionsPerCycle.toFloat()) }
    var selectedFlow by remember { mutableStateOf(currentBreakFlow) }

    // Sync state values on flow updates
    LaunchedEffect(currentWorkSecs, currentShortSecs, currentLongSecs, currentSessionsPerCycle, currentBreakFlow) {
        workMins = (currentWorkSecs / 60).toFloat()
        shortMins = (currentShortSecs / 60).toFloat()
        longMins = (currentLongSecs / 60).toFloat()
        sessionsPerCycle = currentSessionsPerCycle.toFloat()
        selectedFlow = currentBreakFlow
    }

    // Privacy & Terms dialog states
    var showPrivacyDialog by remember { mutableStateOf(false) }
    var showTermsDialog by remember { mutableStateOf(false) }

    // Feedback Form States
    var rating by remember { mutableIntStateOf(0) }
    var feedbackMessage by remember { mutableStateOf("") }
    var feedbackStatus by remember { mutableStateOf("") }
    var isSubmittingFeedback by remember { mutableStateOf(false) }

    // Content launcher to pick GIF
    val pickGifLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        if (uri != null) {
            try {
                context.contentResolver.takePersistableUriPermission(
                    uri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION
                )
            } catch (e: Exception) {}
            TimerService.saveCustomGifUri(context, uri.toString())
            onSettingsSaved()
        }
    }

    // Privacy Dialog
    if (showPrivacyDialog) {
        AlertDialog(
            onDismissRequest = { showPrivacyDialog = false },
            title = { Text("Privacy Policy", fontWeight = FontWeight.Bold) },
            text = {
                Text("GoofyFocus respects your privacy and is committed to protecting your personal data.\n\n1. DATA COLLECTION & PROCESSING (GDPR & CCPA):\nTo manage premium subscriptions across devices, we collect and synchronize select Google account details (Google ID/google_sub, Email, Name, Profile Picture url) and active subscription hours to a secure cloud database (Supabase). Standard app configurations, timers, and focus lists remain stored locally on your device.\n\n2. YOUR RIGHTS (GDPR & CCPA Compliance):\nUnder GDPR and CCPA, you have the right to access, rectify, port, or request the permanent deletion of your account and synchronized data. You can delete your cloud-stored data instantly from within the Settings app page by clicking 'Delete Account & Data'.\n\n3. THIRD-PARTY SERVICES:\nWe integrate AdMob for advertisements. AdMob may collect and process device identifiers or usage logs for analytics and ad personalization.\n\nFor questions, contact marunkumar.datascientist@gmail.com.")
            },
            confirmButton = {
                Button(onClick = { showPrivacyDialog = false }) {
                    Text("Close")
                }
            },
            containerColor = Color(0xFF171415),
            titleContentColor = Color.White,
            textContentColor = Color(0xB3FFFFFF)
        )
    }

    // Mock dialog removed - using real Google Sign-in API on device

    if (showPlayBillingSheet) {
        AlertDialog(
            onDismissRequest = { if (!isProcessingPayment) showPlayBillingSheet = false },
            title = {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("Google Play Billing", fontWeight = FontWeight.Bold, fontSize = 16.sp, color = Color.White)
                    Text("Google Play", color = Color(0xFF34D399), fontWeight = FontWeight.Bold, fontSize = 12.sp)
                }
            },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text(
                        text = "Subscribe to GoofyFocus Premium:",
                        fontSize = 12.sp,
                        color = Color(0xB3FFFFFF)
                    )
                    
                    Card(
                        colors = CardDefaults.cardColors(containerColor = Color(0x0CFFFFFF)),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text(
                                text = "GoofyFocus Premium - $selectedOption",
                                color = Color.White,
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            val priceText = when (selectedOption) {
                                "1 Month" -> "₹199.00 ($2.49) / Month"
                                "6 Months" -> "₹925.00 ($11.49) / 6 Months"
                                else -> "₹1,338.00 ($16.99) / Year"
                            }
                            Text(
                                text = priceText,
                                color = Color(0xFFFCD34D),
                                fontWeight = FontWeight.Bold,
                                fontSize = 13.sp
                            )
                        }
                    }
                    
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Account:", fontSize = 11.sp, color = Color(0x80FFFFFF))
                        Text(googleUserEmail ?: "", fontSize = 11.sp, color = Color.White, fontWeight = FontWeight.Bold)
                    }
                    
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Payment Method:", fontSize = 11.sp, color = Color(0x80FFFFFF))
                        Text("Visa •••• 4242", fontSize = 11.sp, color = Color.White)
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                        val activity = context as? Activity
                        if (activity != null) {
                            val productId = when (selectedOption) {
                                "1 Month" -> "goofyfocus_1month"
                                "6 Months" -> "goofyfocus_6months"
                                else -> "goofyfocus_1year"
                            }
                            billingManager.launchBillingFlow(activity, productId, BillingClient.ProductType.SUBS)
                            showPlayBillingSheet = false
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFFB7185)),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text("Subscribe", fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                if (!isProcessingPayment) {
                    TextButton(onClick = { showPlayBillingSheet = false }) {
                        Text("Cancel", color = Color(0x80FFFFFF))
                    }
                }
            },
            containerColor = Color(0xFF171415)
        )
    }

    // Terms Dialog
    if (showTermsDialog) {
        AlertDialog(
            onDismissRequest = { showTermsDialog = false },
            title = { Text("Terms of Use", fontWeight = FontWeight.Bold) },
            text = {
                Text("By accessing or using GoofyFocus, you agree to be bound by these Terms.\n\n1. LICENSE & USE:\nWe grant you a personal, non-transferable, revocable license to run the app for personal use. Modifying timer variables is allowed.\n\n2. INTELLECTUAL PROPERTY (IP Infringement Protection):\nAll software code, mascots, branding, assets, and design systems are the exclusive intellectual property of GoofyFocus and the developers. Reverse engineering, redistribution, repackaging, or unauthorized commercial copying of this application is strictly prohibited.\n\n3. TIMED PREMIUM SUBSCRIPTIONS:\nPremium features are purchased as dynamic active hours that decrement over elapsed periods. Purchases are non-refundable.\n\n4. DISCLAIMER:\nThe app is provided 'as is' without warranties. We are not liable for productivity losses or data interruptions.")
            },
            confirmButton = {
                Button(onClick = { showTermsDialog = false }) {
                    Text("Close")
                }
            },
            containerColor = Color(0xFF171415),
            titleContentColor = Color.White,
            textContentColor = Color(0xB3FFFFFF)
        )
    }

    if (showDeleteAccountDialog) {
        var isDeleting by remember { mutableStateOf(false) }
        AlertDialog(
            onDismissRequest = { if (!isDeleting) showDeleteAccountDialog = false },
            title = { Text("Delete Account & Data?", fontWeight = FontWeight.Bold) },
            text = {
                Text("Warning: This action is permanent. All subscription details, remaining hours, and account history will be permanently deleted from the cloud. This cannot be undone.")
            },
            confirmButton = {
                Button(
                    onClick = {
                        com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                        coroutineScope.launch {
                            isDeleting = true
                            val sub = googleUserSub
                            if (sub != null) {
                                val success = deleteUserFromSupabase(sub)
                                if (success) {
                                    TimerService.signOutUser(context)
                                    showDeleteAccountDialog = false
                                    android.widget.Toast.makeText(context, "Account and data deleted successfully.", android.widget.Toast.LENGTH_LONG).show()
                                } else {
                                    android.widget.Toast.makeText(context, "Deletion failed. Check network connection.", android.widget.Toast.LENGTH_LONG).show()
                                }
                            }
                            isDeleting = false
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFFB7185)),
                    enabled = !isDeleting
                ) {
                    Text(if (isDeleting) "Deleting... ⏳" else "Delete Permanently", fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                if (!isDeleting) {
                    TextButton(onClick = { showDeleteAccountDialog = false }) {
                        Text("Cancel", color = Color.White)
                    }
                }
            },
            containerColor = Color(0xFF171415),
            titleContentColor = Color.White,
            textContentColor = Color(0xB3FFFFFF)
        )
    }

    if (isCheckingProOnLogin) {
        AlertDialog(
            onDismissRequest = {},
            title = { Text("Restoring Account", color = Color.White) },
            text = {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(16.dp),
                    modifier = Modifier.padding(8.dp)
                ) {
                    CircularProgressIndicator(color = Color(0xFF34D399))
                    Text("Checking cloud status... ⏳", color = Color.White)
                }
            },
            confirmButton = {},
            containerColor = Color(0xFF171415)
        )
    }

    // Ad dialog removed in favor of real AdMob flow.

    AnimatedVisibility(
        visible = isVisible,
        enter = slideInHorizontally(initialOffsetX = { it }) + fadeIn(),
        exit = slideOutHorizontally(targetOffsetX = { it }) + fadeOut()
    ) {
        Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings", color = Color.White, fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = {
                        com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                        handleBack()
                    }) {
                        Icon(
                            imageVector = Icons.Default.ArrowBack,
                            contentDescription = "Back",
                            tint = Color.White
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF0F0D0E),
                    titleContentColor = Color.White
                )
            )
        },
        containerColor = Color(0xFF0F0D0E),
        modifier = modifier
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .padding(innerPadding)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            // Premium Ad Pass Card (24h Free Pass)
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0x11A78BFA)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0x26A78BFA), RoundedCornerShape(16.dp))
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text(
                        text = "✨ 24-Hour Sound & Theme Pass ✨",
                        fontWeight = FontWeight.Bold,
                        fontSize = 15.sp,
                        color = Color(0xFFA78BFA)
                    )
                    
                    val isPermanent = isPro && proExpiryTime == 0L && premiumHours == 0
                    
                    if (isPro) {
                        Text(
                            text = when {
                                isPermanent -> "Lifetime Premium Active! Thank you! 👑"
                                premiumHours > 0 -> {
                                    val days = premiumHours / 24
                                    val hrs = premiumHours % 24
                                    if (days > 0) "Premium Active! 🎟️\n($days days $hrs hours remaining)"
                                    else "Premium Active! 🎟️\n($premiumHours hours remaining)"
                                }
                                else -> "Premium Pass Active! 🎟️\n($remainingTimeText)"
                            },
                            fontSize = 13.sp,
                            color = Color(0xFF34D399),
                            textAlign = TextAlign.Center,
                            fontWeight = FontWeight.Bold
                        )
                    } else {
                        Text(
                            text = "Unlock all premium features (Custom Mascots, Custom GIFs, Custom times, & Focus Sounds) free for 24 hours by watching an ad!",
                            fontSize = 12.sp,
                            color = Color(0xB3FFFFFF),
                            textAlign = TextAlign.Center
                        )
                        
                        val isAdReady by MainActivity.isAdLoaded.collectAsState()
                        
                        Button(
                            onClick = {
                                val activity = context as? android.app.Activity
                                if (activity != null && isAdReady) {
                                    MainActivity.showRewardedAd(
                                        activity,
                                        onRewardEarned = {
                                            TimerService.grant24HourPass(context)
                                            android.widget.Toast.makeText(context, "Premium unlocked for 24 hours! 🎉", android.widget.Toast.LENGTH_SHORT).show()
                                        },
                                        onAdClosedOrFailed = {
                                            android.widget.Toast.makeText(context, "Failed to load ad. Please try again.", android.widget.Toast.LENGTH_SHORT).show()
                                        }
                                    )
                                } else {
                                    android.widget.Toast.makeText(context, "Ad is loading, please try again in a few seconds.", android.widget.Toast.LENGTH_SHORT).show()
                                }
                            },
                            shape = RoundedCornerShape(10.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Color(0xFFA78BFA),
                                contentColor = Color.White
                            ),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                text = if (isAdReady) "Watch Ad to Unlock (24h) 🎟️" else "Ad Loading... ⏳",
                                fontWeight = FontWeight.Bold,
                                fontSize = 13.sp
                            )
                        }
                    }
                }
            }

            // Account & Sync Section
            Text(
                text = "ACCOUNT & SYNC",
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF34D399),
                letterSpacing = 1.5.sp
            )

            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0x1134D399)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0x2634D399), RoundedCornerShape(16.dp))
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    if (googleUserSub == null) {
                        Text(
                            text = "Sign in to synchronize your premium subscription and settings across devices.",
                            fontSize = 12.sp,
                            color = Color(0xB3FFFFFF),
                            textAlign = TextAlign.Center
                        )
                        Button(
                            onClick = {
                                com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                pendingPurchaseOnLogin = false
                                googleSignInLauncher.launch(googleSignInClient.signInIntent)
                            },
                            shape = RoundedCornerShape(10.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Color(0xFF34D399),
                                contentColor = Color(0xFF0F0D0E)
                            ),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Sign in with Google", fontWeight = FontWeight.Bold)
                        }
                    } else {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(40.dp)
                                    .clip(androidx.compose.foundation.shape.CircleShape)
                                    .background(
                                        androidx.compose.ui.graphics.Brush.linearGradient(
                                            colors = listOf(Color(0xFF34D399), Color(0xFF10B981))
                                        )
                                    ),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = googleUserName?.take(1) ?: "U",
                                    color = Color.White,
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 16.sp
                                )
                            }
                            Column(modifier = Modifier.padding(start = 12.dp).weight(1f)) {
                                Text(googleUserName ?: "Google User", color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                                Text(googleUserEmail ?: "", color = Color(0x80FFFFFF), fontSize = 12.sp)
                            }
                            
                            Button(
                                onClick = {
                                    com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                    googleSignInClient.signOut().addOnCompleteListener {
                                        TimerService.signOutUser(context)
                                        android.widget.Toast.makeText(context, "Signed out successfully", android.widget.Toast.LENGTH_SHORT).show()
                                    }
                                },
                                shape = RoundedCornerShape(8.dp),
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = Color(0x1EFB7185),
                                    contentColor = Color(0xFFFB7185)
                                )
                            ) {
                                Text("Sign Out", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "Delete Account & Data",
                            color = Color(0xFFFB7185),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier
                                .align(Alignment.End)
                                .clickable {
                                    com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                    showDeleteAccountDialog = true
                                }
                        )
                    }
                }
            }

            // Upgrade to Premium Section (Redesigned Pill Packages)
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0x11FCD34D)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0x26FCD34D), RoundedCornerShape(16.dp))
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text(
                        text = "👑 GoofyFocus Premium 👑",
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp,
                        color = Color(0xFFFCD34D)
                    )
                    Text(
                        text = "Upgrade to unlock custom sessions, soundscapes, companions, and custom media across your devices.",
                        fontSize = 12.sp,
                        color = Color(0xB3FFFFFF),
                        textAlign = TextAlign.Center
                    )
                    
                    Spacer(modifier = Modifier.height(6.dp))
                    
                    val optionsList = listOf(
                        Triple("1 Month", "₹199.00", "$2.49"),
                        Triple("6 Months", "₹925.00", "$11.49"),
                        Triple("1 Year", "₹1,338.00", "$16.99")
                    )
                    
                    optionsList.forEach { (dur, priceInr, priceUsd) ->
                        val isSelected = selectedOption == dur
                        val bg by animateColorAsState(
                            targetValue = if (isSelected) Color(0xFFFCD34D) else Color(0x0CFFFFFF),
                            label = "option_bg"
                        )
                        val contentColor by animateColorAsState(
                            targetValue = if (isSelected) Color(0xFF0F0D0E) else Color.White,
                            label = "option_text"
                        )
                        val borderCol by animateColorAsState(
                            targetValue = if (isSelected) Color.Transparent else Color(0x1AFFFFFF),
                            label = "option_border"
                        )
                        val strikethroughColor by animateColorAsState(
                            targetValue = if (isSelected) Color(0x990F0D0E) else Color(0x80FFFFFF),
                            label = "option_strikethrough"
                        )
                        
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(16.dp))
                                .background(bg)
                                .border(1.dp, borderCol, RoundedCornerShape(16.dp))
                                .clickable {
                                    com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                    selectedOption = dur
                                }
                                .padding(horizontal = 20.dp, vertical = 14.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text(
                                    text = dur,
                                    fontWeight = FontWeight.Bold,
                                    color = contentColor,
                                    fontSize = 14.sp
                                )
                                if (dur == "1 Year") {
                                    Text(
                                        text = " 👍",
                                        fontSize = 14.sp
                                    )
                                }
                            }
                            
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                if (dur == "6 Months") {
                                    Text(
                                        text = "₹1,194 ($14.94) ",
                                        style = androidx.compose.ui.text.TextStyle(textDecoration = androidx.compose.ui.text.style.TextDecoration.LineThrough),
                                        color = strikethroughColor,
                                        fontSize = 11.sp
                                    )
                                    Text(
                                        text = "→ ",
                                        color = contentColor,
                                        fontSize = 12.sp
                                    )
                                } else if (dur == "1 Year") {
                                    Text(
                                        text = "₹2,388 ($29.88) ",
                                        style = androidx.compose.ui.text.TextStyle(textDecoration = androidx.compose.ui.text.style.TextDecoration.LineThrough),
                                        color = strikethroughColor,
                                        fontSize = 11.sp
                                    )
                                    Text(
                                        text = "→ ",
                                        color = contentColor,
                                        fontSize = 12.sp
                                    )
                                }
                                
                                Text(
                                    text = "$priceInr ($priceUsd)",
                                    fontWeight = FontWeight.Bold,
                                    color = contentColor,
                                    fontSize = 13.sp
                                )
                                
                                if (isSelected) {
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text("✓", fontWeight = FontWeight.Bold, color = contentColor, fontSize = 14.sp)
                                }
                            }
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                    }
                    
                    Spacer(modifier = Modifier.height(6.dp))
                    
                    if (isPro) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            val statusLabel = when {
                                proExpiryTime == 0L && premiumHours == 0 -> "Lifetime Premium Active 👑"
                                premiumHours > 0 -> {
                                    val days = premiumHours / 24
                                    val hrs = premiumHours % 24
                                    if (days > 0) "Premium Active: $days days $hrs hours ✓"
                                    else "Premium Active: $premiumHours hours ✓"
                                }
                                else -> "Premium Pass Active 🎟️"
                            }
                            Text(
                                text = statusLabel,
                                color = Color(0xFF34D399),
                                fontWeight = FontWeight.Bold,
                                fontSize = 13.sp
                            )
                        }
                    } else {
                        Button(
                            onClick = {
                                com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                if (googleUserSub == null) {
                                    pendingPurchaseOnLogin = true
                                    googleSignInLauncher.launch(googleSignInClient.signInIntent)
                                } else {
                                    showPlayBillingSheet = true
                                }
                            },
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Color(0xFFFB7185),
                                contentColor = Color.White
                            ),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            val actionLabel = if (googleUserSub == null) "Sign in with Google to Buy" else "Subscribe with Google Play"
                            Text(actionLabel, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }

            // Overlay Permission Warning (if not granted under Jakob's Law)
            val hasOverlayPermission by com.arunkumar.goofyfocus.MainActivity.hasOverlayPermission.collectAsState()
            if (!hasOverlayPermission) {
                Card(
                    colors = CardDefaults.cardColors(containerColor = Color(0x1EFBBF24)), // Amber translucent warning
                    shape = RoundedCornerShape(16.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Text(
                            text = "Overlay Permission Required ⚠️",
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp,
                            color = Color(0xFFFBBF24)
                        )
                        Text(
                            text = "To display break screens automatically when you are using other apps, GoofyFocus needs permission to draw over other windows.",
                            fontSize = 12.sp,
                            color = Color(0xB3FFFFFF),
                            textAlign = TextAlign.Center
                        )
                        Button(
                            onClick = {
                                try {
                                    val intent = Intent(
                                        android.provider.Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                                        Uri.parse("package:${context.packageName}")
                                    )
                                    context.startActivity(intent)
                                } catch (e: Exception) {
                                    try {
                                        val intent = Intent(android.provider.Settings.ACTION_MANAGE_OVERLAY_PERMISSION)
                                        context.startActivity(intent)
                                    } catch (ex: Exception) {}
                                }
                            },
                            shape = RoundedCornerShape(10.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Color(0xFFFBBF24),
                                contentColor = Color(0xFF1E1B4B)
                            )
                        ) {
                            Text("Grant Permission", fontSize = 13.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }

            // Durations Section Header (Fully Unlocked & Auto-saving)
            Text(
                text = "SESSION DURATIONS",
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFFFB7185),
                letterSpacing = 1.5.sp
            )

            // Durations Settings Card
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0x11FB7185)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0x26FB7185), RoundedCornerShape(16.dp))
                    .then(
                        if (!isPro) {
                            Modifier.clickable {
                                com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                android.widget.Toast.makeText(context, "Premium features are locked. Get a Free Ad Pass or subscribe! 👑", android.widget.Toast.LENGTH_SHORT).show()
                            }
                        } else Modifier
                    )
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    if (!isPro) {
                        Text(
                            text = "🔒 Custom times are locked to default 25/5/10m. Get a Premium Pass to unlock!",
                            color = Color(0xFFFB7185),
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                    
                    // Work Duration Slider
                    Column {
                        Row(
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Work Phase", color = Color.White, fontSize = 14.sp)
                            Text("${(if (isPro) workMins else 25f).toInt()}m", color = if (isPro) Color(0xFFFB7185) else Color.Gray, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                        Slider(
                            value = if (isPro) workMins else 25f,
                            onValueChange = { if (isPro) workMins = it },
                            onValueChangeFinished = {
                                com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                if (isPro) {
                                    TimerService.updateSettings(context, workMins.toInt(), shortMins.toInt(), longMins.toInt(), selectedFlow)
                                    onSettingsSaved()
                                }
                            },
                            enabled = isPro,
                            valueRange = 5f..60f,
                            steps = 11,
                            colors = SliderDefaults.colors(
                                thumbColor = if (isPro) Color(0xFFFB7185) else Color.Gray,
                                activeTrackColor = if (isPro) Color(0xFFFB7185) else Color.DarkGray,
                                inactiveTrackColor = Color(0x33FFFFFF)
                            )
                        )
                    }

                    // Short Break Duration Slider
                    Column {
                        Row(
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Short Break", color = Color.White, fontSize = 14.sp)
                            Text("${(if (isPro) shortMins else 5f).toInt()}m", color = if (isPro) Color(0xFFFB7185) else Color.Gray, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                        Slider(
                            value = if (isPro) shortMins else 5f,
                            onValueChange = { if (isPro) shortMins = it },
                            onValueChangeFinished = {
                                com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                if (isPro) {
                                    TimerService.updateSettings(context, workMins.toInt(), shortMins.toInt(), longMins.toInt(), selectedFlow)
                                    onSettingsSaved()
                                }
                            },
                            enabled = isPro,
                            valueRange = 1f..20f,
                            steps = 19,
                            colors = SliderDefaults.colors(
                                thumbColor = if (isPro) Color(0xFFFB7185) else Color.Gray,
                                activeTrackColor = if (isPro) Color(0xFFFB7185) else Color.DarkGray,
                                inactiveTrackColor = Color(0x33FFFFFF)
                            )
                        )
                    }

                    // Long Break Duration Slider
                    Column {
                        Row(
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Long Break", color = Color.White, fontSize = 14.sp)
                            Text("${(if (isPro) longMins else 10f).toInt()}m", color = if (isPro) Color(0xFFFB7185) else Color.Gray, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                        Slider(
                            value = if (isPro) longMins else 10f,
                            onValueChange = { if (isPro) longMins = it },
                            onValueChangeFinished = {
                                com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                if (isPro) {
                                    TimerService.updateSettings(context, workMins.toInt(), shortMins.toInt(), longMins.toInt(), selectedFlow)
                                    onSettingsSaved()
                                }
                            },
                            enabled = isPro,
                            valueRange = 5f..45f,
                            steps = 8,
                            colors = SliderDefaults.colors(
                                thumbColor = if (isPro) Color(0xFFFB7185) else Color.Gray,
                                activeTrackColor = if (isPro) Color(0xFFFB7185) else Color.DarkGray,
                                inactiveTrackColor = Color(0x33FFFFFF)
                            )
                        )
                    }
                }
            }

            // Custom Media Section Header
            Text(
                text = "CUSTOM BREAK GIF",
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFFA78BFA),
                letterSpacing = 1.5.sp
            )

            // Custom Media Card
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0x11A78BFA)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0x26A78BFA), RoundedCornerShape(16.dp))
                    .then(
                        if (!isPro) {
                            Modifier.clickable {
                                com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                android.widget.Toast.makeText(context, "Premium features are locked. Get a Free Ad Pass or subscribe! 👑", android.widget.Toast.LENGTH_SHORT).show()
                            }
                        } else Modifier
                    )
            ) {
                Column(
                    modifier = Modifier
                        .padding(16.dp)
                        .graphicsLayer(alpha = if (isPro) 1.0f else 0.6f),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text(
                        text = "Customize the background GIF that displays during breaks (or use default packaged gifs).",
                        color = Color(0xB3FFFFFF),
                        fontSize = 13.sp
                    )
                    
                    Row(
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Button(
                            onClick = { 
                                com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                if (isPro) {
                                    pickGifLauncher.launch("image/*") 
                                } else {
                                    android.widget.Toast.makeText(context, "Premium features are locked. Get a Free Ad Pass or subscribe! 👑", android.widget.Toast.LENGTH_SHORT).show()
                                }
                            },
                            enabled = true,
                            shape = RoundedCornerShape(8.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Color(0xFFA78BFA),
                                contentColor = Color.White
                            )
                        ) {
                            Text("Select Break GIF", fontSize = 13.sp)
                        }

                        if (customGifUri != null) {
                            TextButton(
                                onClick = {
                                    if (isPro) {
                                        TimerService.saveCustomGifUri(context, null)
                                        onSettingsSaved()
                                    }
                                },
                                enabled = isPro
                            ) {
                                Text("Clear Custom GIF", color = Color(0xFFFB7185), fontSize = 12.sp)
                            }
                        }
                    }

                    if (!isPro) {
                        Text(
                            text = "🔒 Premium Feature: Get a Free Ad Pass to unlock.",
                            color = Color(0xFFFB7185),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold
                        )
                    } else {
                        Text(
                            text = if (customGifUri != null) "Selected: Custom Break GIF Active" else "Selected: Using Default Packaged GIFs",
                            color = if (customGifUri != null) Color(0xFF34D399) else Color(0x80FFFFFF),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
            }

            // Mascot Companion Section Header
            Text(
                text = "MASCOT COMPANION",
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFFFCD34D),
                letterSpacing = 1.5.sp
            )

            // Mascot Companion Settings Card
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0x11FCD34D)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0x26FCD34D), RoundedCornerShape(16.dp))
                    .then(
                        if (!isPro) {
                            Modifier.clickable {
                                com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                android.widget.Toast.makeText(context, "Premium features are locked. Get a Free Ad Pass or subscribe! 👑", android.widget.Toast.LENGTH_SHORT).show()
                            }
                        } else Modifier
                    )
            ) {
                Column(
                    modifier = Modifier
                        .padding(16.dp)
                        .graphicsLayer(alpha = if (isPro) 1.0f else 0.6f),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text("Select Mascot Companion", color = Color.White, fontSize = 14.sp)
                    
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        val mascotOptions = listOf(
                            "cat" to "Goofy Cat 🐱",
                            "dog" to "Cute Dog 🐶"
                        )
                        mascotOptions.forEach { (value, label) ->
                            val isSelected = mascotType == value
                            val animatedBg by animateColorAsState(
                                targetValue = if (isSelected) Color(0xFFFCD34D).copy(alpha = 0.15f) else Color(0x0CFFFFFF),
                                label = "mascot_bg"
                            )
                            val animatedBorder by animateColorAsState(
                                targetValue = if (isSelected) Color(0xFFFCD34D) else Color(0x1AFFFFFF),
                                label = "mascot_border"
                            )
                            val textColor by animateColorAsState(
                                targetValue = if (isSelected) Color(0xFFFCD34D) else Color.White,
                                label = "mascot_text"
                            )
                            
                            Box(
                                modifier = Modifier
                                    .weight(1f)
                                    .clip(RoundedCornerShape(12.dp))
                                    .background(animatedBg)
                                    .border(1.dp, animatedBorder, RoundedCornerShape(12.dp))
                                    .clickable {
                                        com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                        if (isPro) {
                                            TimerService.setMascotType(context, value)
                                            onSettingsSaved()
                                        } else {
                                            android.widget.Toast.makeText(context, "Premium features are locked. Get a Free Ad Pass or subscribe! 👑", android.widget.Toast.LENGTH_SHORT).show()
                                        }
                                    }
                                    .padding(vertical = 12.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = label,
                                    color = textColor,
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                    fontSize = 13.sp
                                )
                            }
                        }
                    }
                    if (!isPro) {
                        Text(
                            text = "🔒 Premium Feature: Get a Free Ad Pass to unlock.",
                            color = Color(0xFFFCD34D),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }

            // Break Flow Section Header
            Text(
                text = "BREAK FLOW & STRATEGY",
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFFA78BFA),
                letterSpacing = 1.5.sp
            )

            // Break Flow Settings Card
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0x11A78BFA)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0x26A78BFA), RoundedCornerShape(16.dp))
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Sessions Per Cycle
                    Column {
                        Row(
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Sessions before Long Break", color = Color.White, fontSize = 14.sp)
                            Text("${(if (isPro) sessionsPerCycle else 4f).toInt()}", color = if (isPro) Color(0xFFA78BFA) else Color.Gray, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                        Slider(
                            value = if (isPro) sessionsPerCycle else 4f,
                            onValueChange = { if (isPro) sessionsPerCycle = it },
                            onValueChangeFinished = {
                                if (isPro) {
                                    TimerService.sessionsPerCycle.value = sessionsPerCycle.toInt()
                                    val editor = context.getSharedPreferences("GoofyFocusPrefs", Context.MODE_PRIVATE).edit()
                                    editor.putInt("SESSIONS_PER_CYCLE", sessionsPerCycle.toInt()).apply()
                                    onSettingsSaved()
                                }
                            },
                            enabled = isPro,
                            valueRange = 2f..8f,
                            steps = 5,
                            colors = SliderDefaults.colors(
                                thumbColor = if (isPro) Color(0xFFA78BFA) else Color.Gray,
                                activeTrackColor = if (isPro) Color(0xFFA78BFA) else Color.DarkGray,
                                inactiveTrackColor = Color(0x33FFFFFF)
                            )
                        )
                    }

                    HorizontalDivider(color = Color(0x1AFFFFFF))

                    // Flow Mode Selection (Auto-saves on click)
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Break Flow Strategy", color = Color.White, fontSize = 14.sp, modifier = Modifier.padding(bottom = 6.dp))
                        
                        val flowOptions = listOf(
                            "auto" to "Auto-Cycling (25/5/25/5/25/15) 🔄",
                            "always_short" to "Always Short Breaks ☕",
                            "always_long" to "Always Long Breaks 🛌"
                        )

                        flowOptions.forEach { (value, label) ->
                            val isSelected = selectedFlow == value
                            val animatedBg by animateColorAsState(
                                targetValue = if (isSelected) Color(0xFFA78BFA).copy(alpha = 0.15f) else Color(0x0CFFFFFF),
                                label = "flow_bg"
                            )
                            val animatedBorder by animateColorAsState(
                                targetValue = if (isSelected) Color(0xFFA78BFA) else Color(0x1AFFFFFF),
                                label = "flow_border"
                            )
                            val textColor by animateColorAsState(
                                targetValue = if (isSelected) Color(0xFFA78BFA) else Color.White,
                                label = "flow_text"
                            )
                            
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(12.dp))
                                    .background(animatedBg)
                                    .border(1.dp, animatedBorder, RoundedCornerShape(12.dp))
                                    .clickable {
                                        com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                        selectedFlow = value
                                        TimerService.updateSettings(context, workMins.toInt(), shortMins.toInt(), longMins.toInt(), value)
                                        onSettingsSaved()
                                    }
                                    .padding(horizontal = 16.dp, vertical = 14.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = label,
                                    color = textColor,
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                    fontSize = 13.sp,
                                    modifier = Modifier.weight(1f)
                                )
                                if (isSelected) {
                                    Icon(
                                        imageVector = Icons.Default.Star,
                                        contentDescription = "Selected",
                                        tint = Color(0xFFA78BFA),
                                        modifier = Modifier.size(16.dp)
                                    )
                                }
                            }
                            Spacer(modifier = Modifier.height(8.dp))
                        }
                    }
                }
            }

            // PC Version Promotion Card
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0x0C3B82F6)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0x263B82F6), RoundedCornerShape(16.dp))
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text(
                        text = "Try GoofyFocus for Desktop! 💻",
                        fontWeight = FontWeight.Bold,
                        fontSize = 15.sp,
                        color = Color(0xFF60A5FA)
                    )
                    Text(
                        text = "Take your focus to the next level on PC & Mac! Customize full GIF folder packs, manage sound alerts, access detailed productivity charts, and support development directly via our desktop app.",
                        fontSize = 12.sp,
                        color = Color(0xB3FFFFFF),
                        textAlign = TextAlign.Center
                    )
                    Button(
                        onClick = {
                            try {
                                val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://arunkumarm-git.github.io/GoofyFocus/"))
                                context.startActivity(intent)
                            } catch (e: Exception) {}
                        },
                        shape = RoundedCornerShape(10.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF3B82F6),
                            contentColor = Color.White
                        )
                    ) {
                        Text("Get Desktop Version", fontSize = 13.sp)
                    }
                }
            }

            // Feedback Section
            Text(
                text = "FEEDBACK",
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFFFB7185),
                letterSpacing = 1.5.sp
            )

            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0x11FB7185)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0x26FB7185), RoundedCornerShape(16.dp))
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text("How is your experience with GoofyFocus?", color = Color.White, fontSize = 13.sp)
                    
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        for (i in 1..5) {
                            val isSelected = i <= rating
                            val scale by animateFloatAsState(
                                targetValue = if (isSelected) 1.25f else 1.0f,
                                animationSpec = spring(
                                    dampingRatio = Spring.DampingRatioMediumBouncy,
                                    stiffness = Spring.StiffnessLow
                                ),
                                label = "star_scale"
                            )
                            Icon(
                                imageVector = Icons.Filled.Star,
                                contentDescription = "Star $i",
                                tint = if (isSelected) Color(0xFFFCD34D) else Color(0x22FFFFFF),
                                modifier = Modifier
                                    .size(36.dp)
                                    .graphicsLayer {
                                        scaleX = scale
                                        scaleY = scale
                                    }
                                    .clickable {
                                        com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                        rating = i
                                    }
                            )
                        }
                    }

                    TextField(
                        value = feedbackMessage,
                        onValueChange = { feedbackMessage = it },
                        placeholder = { Text("What could be better? (optional)", color = Color(0x66FFFFFF), fontSize = 13.sp) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(100.dp),
                        colors = TextFieldDefaults.colors(
                            focusedContainerColor = Color(0x0DFFFFFF),
                            unfocusedContainerColor = Color(0x0DFFFFFF),
                            focusedTextColor = Color.White,
                            unfocusedTextColor = Color.White,
                            focusedIndicatorColor = Color(0xFFFB7185),
                            unfocusedIndicatorColor = Color.Transparent
                        )
                    )

                    Button(
                        onClick = {
                            if (rating == 0) {
                                feedbackStatus = "Please select a rating ★"
                                return@Button
                            }
                            coroutineScope.launch {
                                isSubmittingFeedback = true
                                feedbackStatus = "Sending..."
                                val success = sendFeedbackToSupabase(rating, feedbackMessage)
                                isSubmittingFeedback = false
                                if (success) {
                                    feedbackStatus = "✓ Thanks for your feedback!"
                                    feedbackMessage = ""
                                    rating = 0
                                } else {
                                    feedbackStatus = "Error sending. Check connection."
                                }
                            }
                        },
                        enabled = !isSubmittingFeedback,
                        shape = RoundedCornerShape(10.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0x1EFB7185),
                            contentColor = Color(0xFFFB7185)
                        ),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = if (isSubmittingFeedback) "Sending..." else "Send Feedback",
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 13.sp
                        )
                    }

                    if (feedbackStatus.isNotEmpty()) {
                        Text(
                            text = feedbackStatus,
                            color = Color(0x80FFFFFF),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Medium,
                            modifier = Modifier.align(Alignment.CenterHorizontally)
                        )
                    }
                }
            }

            // Legal & Policies (Familiar standard UX under Jakob's Law)
            Text(
                text = "LEGAL & POLICIES",
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0x80FFFFFF),
                letterSpacing = 1.5.sp
            )

            // Legal Settings Card
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0x0CFFFFFF)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0x1AFFFFFF), RoundedCornerShape(16.dp))
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    Text(
                        text = "Privacy Policy",
                        color = Color.White,
                        fontSize = 14.sp,
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { showPrivacyDialog = true }
                    )
                    
                    HorizontalDivider(color = Color(0x1AFFFFFF))

                    Text(
                        text = "Terms of Use",
                        color = Color.White,
                        fontSize = 14.sp,
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { showTermsDialog = true }
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Jakob's Law standard Go Back / Close Button (Settings are auto-saved)
            Button(
                onClick = {
                    com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                    handleBack()
                },
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0x1EFFFFFF),
                    contentColor = Color.White
                ),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp)
            ) {
                Text("Go Back", fontWeight = FontWeight.Bold, fontSize = 15.sp)
            }
            Text(
                text = if (saveTrigger > 0) "Saved automatically ✓" else "Settings are saved automatically.",
                color = saveIndicatorColor,
                fontSize = 11.sp,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth()
            )
        }
    }
}
}

private suspend fun syncUserToSupabase(
    sub: String,
    email: String,
    name: String?,
    picture: String?,
    isPro: Boolean,
    hours: Int
): Boolean {
    return withContext(Dispatchers.IO) {
        var attempts = 0
        val maxAttempts = 3
        var success = false
        
        while (attempts < maxAttempts && !success) {
            attempts++
            var conn: HttpURLConnection? = null
            try {
                val url = URL("https://nqshkkzrnsafnfvujanr.supabase.co/rest/v1/users?on_conflict=google_sub")
                conn = url.openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.connectTimeout = 10000
                conn.readTimeout = 10000
                conn.setRequestProperty("apikey", "sb_publishable_O-jmtJ8nx11HO0kR8D7mzw_uVsyRqFq")
                conn.setRequestProperty("Authorization", "Bearer sb_publishable_O-jmtJ8nx11HO0kR8D7mzw_uVsyRqFq")
                conn.setRequestProperty("Content-Type", "application/json")
                conn.setRequestProperty("Prefer", "resolution=merge-duplicates")
                conn.doOutput = true
                
                val cleanName = name ?: "Google User"
                val jsonBody = """
                    {
                        "google_sub": "$sub",
                        "email": "$email",
                        "given_name": "$cleanName",
                        "picture_url": "${picture ?: ""}",
                        "is_pro": $isPro,
                        "premium_hours": $hours,
                        "last_premium_sync_at": ${if (isPro) "\"now()\"" else "null"},
                        "platform": "Mobile",
                        "last_seen_at": "now()"
                    }
                """.trimIndent()
                
                OutputStreamWriter(conn.outputStream).use { writer ->
                    writer.write(jsonBody)
                    writer.flush()
                }
                
                val responseCode = conn.responseCode
                if (responseCode in 200..299) {
                    success = true
                } else {
                    val errorText = conn.errorStream?.bufferedReader()?.use { it.readText() } ?: ""
                    android.util.Log.e("Supabase", "syncUserToSupabase failed on attempt $attempts with code $responseCode: $errorText")
                    if (responseCode in 400..499 && responseCode != 429) {
                        break
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("Supabase", "syncUserToSupabase exception on attempt $attempts: ${e.message}", e)
                if (attempts >= maxAttempts) {
                    break
                }
            } finally {
                conn?.disconnect()
            }
            if (!success && attempts < maxAttempts) {
                kotlinx.coroutines.delay(2000L * attempts)
            }
        }
        success
    }
}

private suspend fun checkProStatusFromSupabase(email: String): Pair<Int, Long>? {
    return withContext(Dispatchers.IO) {
        var attempts = 0
        val maxAttempts = 3
        var result: Pair<Int, Long>? = null
        var shouldRetry = true
        
        while (attempts < maxAttempts && shouldRetry && result == null) {
            attempts++
            var conn: HttpURLConnection? = null
            try {
                val url = URL("https://nqshkkzrnsafnfvujanr.supabase.co/rest/v1/users?email=eq.$email")
                conn = url.openConnection() as HttpURLConnection
                conn.requestMethod = "GET"
                conn.connectTimeout = 10000
                conn.readTimeout = 10000
                conn.setRequestProperty("apikey", "sb_publishable_O-jmtJ8nx11HO0kR8D7mzw_uVsyRqFq")
                conn.setRequestProperty("Authorization", "Bearer sb_publishable_O-jmtJ8nx11HO0kR8D7mzw_uVsyRqFq")
                conn.setRequestProperty("Accept", "application/json")
                
                val responseCode = conn.responseCode
                if (responseCode in 200..299) {
                    val responseText = conn.inputStream.bufferedReader().use { it.readText() }
                    
                    val rows = responseText.split(Regex("\\},\\s*\\{"))
                    var maxHours = 0
                    var bestSyncTime = 0L
                    var foundPro = false
                    
                    for (row in rows) {
                        if (row.contains("\"is_pro\":true") || row.contains("\"is_pro\": true")) {
                            foundPro = true
                            var hours = 0
                            val hoursMarker = "\"premium_hours\""
                            val markerIdx = row.indexOf(hoursMarker)
                            if (markerIdx != -1) {
                                var idx = markerIdx + hoursMarker.length
                                while (idx < row.length && (row[idx] == ' ' || row[idx] == ':')) {
                                    idx++
                                }
                                val start = idx
                                var end = start
                                while (end < row.length && (row[end].isDigit() || row[end] == '-')) {
                                    end++
                                }
                                hours = row.substring(start, end).toIntOrNull() ?: 0
                            }
                            
                            var syncTime = System.currentTimeMillis()
                            val syncMarker = "\"last_premium_sync_at\""
                            val sMarkerIdx = row.indexOf(syncMarker)
                            if (sMarkerIdx != -1) {
                                var idx = sMarkerIdx + syncMarker.length
                                while (idx < row.length && (row[idx] == ' ' || row[idx] == ':' || row[idx] == '"')) {
                                    idx++
                                }
                                val start = idx
                                var end = start
                                while (end < row.length && row[end] != '"') {
                                    end++
                                }
                                val timeStr = row.substring(start, end)
                                try {
                                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                                        val instant = java.time.Instant.parse(timeStr)
                                        syncTime = instant.toEpochMilli()
                                    } else {
                                        syncTime = System.currentTimeMillis()
                                    }
                                } catch (e: Exception) {
                                    e.printStackTrace()
                                }
                            }
                            
                            if (hours > maxHours || (hours == maxHours && syncTime > bestSyncTime)) {
                                maxHours = hours
                                bestSyncTime = syncTime
                            }
                        }
                    }
                    
                    if (foundPro) {
                        result = Pair(maxHours, bestSyncTime)
                    } else {
                        shouldRetry = false // Valid response, just not pro
                    }
                } else {
                    val errorText = conn.errorStream?.bufferedReader()?.use { it.readText() } ?: ""
                    android.util.Log.e("Supabase", "checkProStatusFromSupabase failed on attempt $attempts with code $responseCode: $errorText")
                    if (responseCode in 400..499 && responseCode != 429) {
                        shouldRetry = false
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("Supabase", "checkProStatusFromSupabase exception on attempt $attempts: ${e.message}", e)
                if (attempts >= maxAttempts) {
                    shouldRetry = false
                }
            } finally {
                conn?.disconnect()
            }
            if (result == null && shouldRetry && attempts < maxAttempts) {
                kotlinx.coroutines.delay(2000L * attempts)
            }
        }
        result
    }
}

private suspend fun sendFeedbackToSupabase(rating: Int, message: String): Boolean {
    return withContext(Dispatchers.IO) {
        var attempts = 0
        val maxAttempts = 3
        var success = false
        
        while (attempts < maxAttempts && !success) {
            attempts++
            var conn: HttpURLConnection? = null
            try {
                val url = URL("https://nqshkkzrnsafnfvujanr.supabase.co/rest/v1/feedback")
                conn = url.openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.connectTimeout = 10000
                conn.readTimeout = 10000
                conn.setRequestProperty("apikey", "sb_publishable_O-jmtJ8nx11HO0kR8D7mzw_uVsyRqFq")
                conn.setRequestProperty("Authorization", "Bearer sb_publishable_O-jmtJ8nx11HO0kR8D7mzw_uVsyRqFq")
                conn.setRequestProperty("Content-Type", "application/json")
                conn.setRequestProperty("Prefer", "return=minimal")
                conn.doOutput = true
                
                val jsonBody = """
                    {
                        "email": "android-user",
                        "rating": $rating,
                        "message": "${message.replace("\"", "\\\"").replace("\n", "\\n")}"
                    }
                """.trimIndent()
                
                OutputStreamWriter(conn.outputStream).use { writer ->
                    writer.write(jsonBody)
                    writer.flush()
                }
                
                val responseCode = conn.responseCode
                if (responseCode in 200..299) {
                    success = true
                } else {
                    val errorText = conn.errorStream?.bufferedReader()?.use { it.readText() } ?: ""
                    android.util.Log.e("Supabase", "sendFeedbackToSupabase failed on attempt $attempts with code $responseCode: $errorText")
                    if (responseCode in 400..499 && responseCode != 429) {
                        break
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("Supabase", "sendFeedbackToSupabase exception on attempt $attempts: ${e.message}", e)
                if (attempts >= maxAttempts) {
                    break
                }
            } finally {
                conn?.disconnect()
            }
            if (!success && attempts < maxAttempts) {
                kotlinx.coroutines.delay(2000L * attempts)
            }
        }
        success
    }
}

private suspend fun deleteUserFromSupabase(sub: String): Boolean {
    return withContext(Dispatchers.IO) {
        var attempts = 0
        val maxAttempts = 3
        var success = false
        
        while (attempts < maxAttempts && !success) {
            attempts++
            var conn: HttpURLConnection? = null
            try {
                val url = URL("https://nqshkkzrnsafnfvujanr.supabase.co/rest/v1/users?google_sub=eq.$sub")
                conn = url.openConnection() as HttpURLConnection
                conn.requestMethod = "DELETE"
                conn.connectTimeout = 10000
                conn.readTimeout = 10000
                conn.setRequestProperty("apikey", "sb_publishable_O-jmtJ8nx11HO0kR8D7mzw_uVsyRqFq")
                conn.setRequestProperty("Authorization", "Bearer sb_publishable_O-jmtJ8nx11HO0kR8D7mzw_uVsyRqFq")
                
                val responseCode = conn.responseCode
                if (responseCode in 200..299) {
                    success = true
                } else {
                    val errorText = conn.errorStream?.bufferedReader()?.use { it.readText() } ?: ""
                    android.util.Log.e("Supabase", "deleteUserFromSupabase failed on attempt $attempts with code $responseCode: $errorText")
                    if (responseCode in 400..499 && responseCode != 429) {
                        break
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("Supabase", "deleteUserFromSupabase exception on attempt $attempts: ${e.message}", e)
                if (attempts >= maxAttempts) {
                    break
                }
            } finally {
                conn?.disconnect()
            }
            if (!success && attempts < maxAttempts) {
                kotlinx.coroutines.delay(2000L * attempts)
            }
        }
        success
    }
}
