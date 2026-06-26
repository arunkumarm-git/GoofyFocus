package com.arunkumar.goofyfocus

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.core.content.ContextCompat
import com.arunkumar.goofyfocus.theme.GoofyFocusTheme
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import android.content.Context
import com.google.android.gms.ads.MobileAds
import com.google.android.gms.ads.AdRequest
import com.google.android.gms.ads.LoadAdError
import com.google.android.gms.ads.rewarded.RewardedAd
import com.google.android.gms.ads.rewarded.RewardedAdLoadCallback
import com.google.firebase.Firebase
import com.google.firebase.analytics.analytics
import com.google.firebase.crashlytics.crashlytics


class MainActivity : ComponentActivity() {

    var launchBreakOverlay by mutableStateOf(false)
        private set

    fun consumeBreakOverlayTrigger() {
        launchBreakOverlay = false
    }

    private val requestNotificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        // Notification permission granted or denied
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        hasOverlayPermission.value = android.provider.Settings.canDrawOverlays(this)
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
        } else {
            @Suppress("DEPRECATION")
            window.addFlags(
                android.view.WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                android.view.WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
            )
        }
        
        enableEdgeToEdge()
        checkNotificationPermission()
        handleIntent(intent)

        // Initialize AdMob SDK
        try {
            MobileAds.initialize(this) {}
            loadRewardedAd(this)
        } catch (e: Throwable) {
            e.printStackTrace()
            try {
                Firebase.crashlytics.recordException(e)
            } catch (ex: Exception) {
                ex.printStackTrace()
            }
        }

        setContent {
            GoofyFocusTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val hasPermission by hasOverlayPermission.collectAsState()
                    var showDialog by remember { mutableStateOf(false) }
                    var dismissedStartupPrompt by remember { mutableStateOf(false) }
                    
                    LaunchedEffect(hasPermission, dismissedStartupPrompt) {
                        showDialog = !hasPermission && !dismissedStartupPrompt
                    }

                    // Log app open to Firebase Analytics
                    LaunchedEffect(Unit) {
                        try {
                            Firebase.analytics.logEvent("app_open", null)
                        } catch (ex: Exception) {
                            ex.printStackTrace()
                        }
                    }
                    
                    MainNavigation()
                    
                    if (showDialog) {
                        AlertDialog(
                            onDismissRequest = {
                                showDialog = false
                                dismissedStartupPrompt = true
                            },
                            title = { Text("Display Over Other Apps ⚠️", fontWeight = FontWeight.Bold) },
                            text = {
                                Text("GoofyFocus needs permission to draw over other apps to display the break overlay screen immediately when your work timer expires. This helps you stay disciplined and take breaks on time!")
                            },
                            confirmButton = {
                                Button(
                                    onClick = {
                                        showDialog = false
                                        try {
                                            val intent = Intent(
                                                android.provider.Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                                                Uri.parse("package:${packageName}")
                                            )
                                            startActivity(intent)
                                        } catch (e: Exception) {
                                            try {
                                                val intent = Intent(android.provider.Settings.ACTION_MANAGE_OVERLAY_PERMISSION)
                                                startActivity(intent)
                                            } catch (ex: Exception) {}
                                        }
                                    },
                                    colors = ButtonDefaults.buttonColors(
                                        containerColor = Color(0xFFFB7185),
                                        contentColor = Color.White
                                    )
                                ) {
                                    Text("Grant Permission")
                                }
                            },
                            dismissButton = {
                                Button(
                                    onClick = {
                                        showDialog = false
                                        dismissedStartupPrompt = true
                                    },
                                    colors = ButtonDefaults.buttonColors(
                                        containerColor = Color(0x1EFFFFFF),
                                        contentColor = Color.White
                                    )
                                ) {
                                    Text("Not Now")
                                }
                            },
                            containerColor = Color(0xFF171415),
                            titleContentColor = Color.White,
                            textContentColor = Color(0xB3FFFFFF)
                        )
                    }
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        hasOverlayPermission.value = android.provider.Settings.canDrawOverlays(this)
        if (rewardedAd == null) {
            loadRewardedAd(this)
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }

    private fun handleIntent(intent: Intent?) {
        if (intent != null && intent.getBooleanExtra("LAUNCH_BREAK_OVERLAY", false)) {
            launchBreakOverlay = true
            intent.removeExtra("LAUNCH_BREAK_OVERLAY")
        }
    }

    private fun checkNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            val hasPermission = ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED
            if (!hasPermission) {
                requestNotificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }

    companion object {
        val breakTrigger = MutableSharedFlow<Boolean>(extraBufferCapacity = 1)
        val hasOverlayPermission = MutableStateFlow(true)

        // AdMob load/show states
        var rewardedAd: RewardedAd? = null
        val isAdLoaded = MutableStateFlow(false)

        fun loadRewardedAd(context: Context) {
            try {
                val adRequest = AdRequest.Builder().build()
                val adUnitId = "ca-app-pub-3054785971628758/4600001818"
                
                RewardedAd.load(
                    context,
                    adUnitId,
                    adRequest,
                    object : RewardedAdLoadCallback() {
                        override fun onAdFailedToLoad(adError: LoadAdError) {
                            rewardedAd = null
                            isAdLoaded.value = false
                        }

                        override fun onAdLoaded(ad: RewardedAd) {
                            rewardedAd = ad
                            isAdLoaded.value = true
                        }
                    }
                )
            } catch (e: Throwable) {
                e.printStackTrace()
                try {
                    Firebase.crashlytics.recordException(e)
                } catch (ex: Exception) {
                    ex.printStackTrace()
                }
            }
        }

        fun showRewardedAd(
            activity: android.app.Activity,
            onRewardEarned: () -> Unit,
            onAdClosedOrFailed: () -> Unit
        ) {
            val ad = rewardedAd
            if (ad != null) {
                ad.show(activity) {
                    onRewardEarned()
                }
                rewardedAd = null
                isAdLoaded.value = false
                loadRewardedAd(activity)
            } else {
                onAdClosedOrFailed()
            }
        }
    }
}
