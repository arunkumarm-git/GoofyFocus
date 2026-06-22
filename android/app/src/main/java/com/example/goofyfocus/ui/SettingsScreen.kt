package com.example.goofyfocus.ui

import android.content.Context
import android.content.Intent
import android.net.Uri
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.goofyfocus.TimerService
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
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

    // Donation custom amount state (encourages custom values)
    var donationAmount by remember { mutableStateOf("5.00") }

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

    // Opens PayPal URL
    val openDonationUrl = {
        val amount = donationAmount.toFloatOrNull() ?: 5.00f
        val paypalUrl = "https://www.paypal.com/cgi-bin/webscr?" +
                "cmd=_xclick" +
                "&business=arunkmarthi@gmail.com" +
                "&item_name=GoofyFocus+Support+%26+Donation" +
                "&amount=${String.format("%.2f", amount)}" +
                "&currency_code=USD" +
                "&no_shipping=1" +
                "&no_note=1"
        try {
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(paypalUrl))
            context.startActivity(intent)
            TimerService.setProEnabled(context, true)
        } catch (e: Exception) {}
    }

    // Privacy Dialog
    if (showPrivacyDialog) {
        AlertDialog(
            onDismissRequest = { showPrivacyDialog = false },
            title = { Text("Privacy Policy", fontWeight = FontWeight.Bold) },
            text = {
                Text("GoofyFocus respects your privacy. All countdown timers, work logs, custom break media, and configurations are stored entirely locally on your mobile device.\n\nThe application does not collect, process, track, or share any personal identity, search queries, or user files. The feedback submission form sends anonymously your star rating and comment to a secure database to help improve developers' builds.")
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

    // Terms Dialog
    if (showTermsDialog) {
        AlertDialog(
            onDismissRequest = { showTermsDialog = false },
            title = { Text("Terms of Use", fontWeight = FontWeight.Bold) },
            text = {
                Text("GoofyFocus is a break reminder utility provided 'as is' without warranties of any kind.\n\nYou are permitted to run the compiled application for personal, non-commercial use. Modifying timer variables is allowed. The software is governed by copyright licensing; redistributing or publishing commercial packaging based on this source code requires separately negotiated authorizing rights.")
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
                    IconButton(onClick = { handleBack() }) {
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
            // 1. Donation Card (Encouraging pay-what-you-want donation)
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0x1EFB7185)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text(
                        text = "Support GoofyFocus! 💖",
                        fontWeight = FontWeight.Bold,
                        fontSize = 15.sp,
                        color = Color(0xFFFB7185)
                    )
                    Text(
                        text = "GoofyFocus is fully open-source and free. If you enjoy using this tool to stay focused, consider supporting development by donating what you want!",
                        fontSize = 12.sp,
                        color = Color(0xB3FFFFFF),
                        textAlign = TextAlign.Center
                    )
                    
                    // Amount Input & Button
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        TextField(
                            value = donationAmount,
                            onValueChange = { donationAmount = it },
                            label = { Text("USD Amount") },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                            modifier = Modifier.weight(1f),
                            colors = TextFieldDefaults.colors(
                                focusedContainerColor = Color(0x0DFFFFFF),
                                unfocusedContainerColor = Color(0x0DFFFFFF),
                                focusedTextColor = Color.White,
                                unfocusedTextColor = Color.White
                            )
                        )
                        Button(
                            onClick = openDonationUrl,
                            shape = RoundedCornerShape(10.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Color(0xFFFB7185),
                                contentColor = Color.White
                            )
                        ) {
                            Text("Donate")
                        }
                    }
                    if (isPro) {
                        Text(
                            text = "Thank you so much for your support! ✨",
                            color = Color(0xFF34D399),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }

            // Overlay Permission Warning (if not granted under Jakob's Law)
            val hasOverlayPermission by com.example.goofyfocus.MainActivity.hasOverlayPermission.collectAsState()
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
                colors = CardDefaults.cardColors(containerColor = Color(0x14FFFFFF)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Work Duration Slider
                    Column {
                        Row(
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Work Phase", color = Color.White, fontSize = 14.sp)
                            Text("${workMins.toInt()}m", color = Color(0xFFFB7185), fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                        Slider(
                            value = workMins,
                            onValueChange = { workMins = it },
                            onValueChangeFinished = {
                                TimerService.updateSettings(context, workMins.toInt(), shortMins.toInt(), longMins.toInt(), selectedFlow)
                                onSettingsSaved()
                            },
                            valueRange = 5f..60f,
                            steps = 11,
                            colors = SliderDefaults.colors(
                                thumbColor = Color(0xFFFB7185),
                                activeTrackColor = Color(0xFFFB7185),
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
                            Text("${shortMins.toInt()}m", color = Color(0xFFFB7185), fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                        Slider(
                            value = shortMins,
                            onValueChange = { shortMins = it },
                            onValueChangeFinished = {
                                TimerService.updateSettings(context, workMins.toInt(), shortMins.toInt(), longMins.toInt(), selectedFlow)
                                onSettingsSaved()
                            },
                            valueRange = 1f..20f,
                            steps = 19,
                            colors = SliderDefaults.colors(
                                thumbColor = Color(0xFFFB7185),
                                activeTrackColor = Color(0xFFFB7185),
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
                            Text("${longMins.toInt()}m", color = Color(0xFFFB7185), fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                        Slider(
                            value = longMins,
                            onValueChange = { longMins = it },
                            onValueChangeFinished = {
                                TimerService.updateSettings(context, workMins.toInt(), shortMins.toInt(), longMins.toInt(), selectedFlow)
                                onSettingsSaved()
                            },
                            valueRange = 5f..45f,
                            steps = 8,
                            colors = SliderDefaults.colors(
                                thumbColor = Color(0xFFFB7185),
                                activeTrackColor = Color(0xFFFB7185),
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
                colors = CardDefaults.cardColors(containerColor = Color(0x14FFFFFF)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
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
                            onClick = { pickGifLauncher.launch("image/*") },
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
                                    TimerService.saveCustomGifUri(context, null)
                                    onSettingsSaved()
                                }
                            ) {
                                Text("Clear Custom GIF", color = Color(0xFFFB7185), fontSize = 12.sp)
                            }
                        }
                    }

                    Text(
                        text = if (customGifUri != null) "Selected: Custom Break GIF Active" else "Selected: Using Default Packaged GIFs",
                        color = if (customGifUri != null) Color(0xFF34D399) else Color(0x80FFFFFF),
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium
                    )
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
                colors = CardDefaults.cardColors(containerColor = Color(0x14FFFFFF)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text("Select Mascot Companion", color = Color.White, fontSize = 14.sp)
                    
                    val mascotOptions = listOf(
                        "cat" to "Goofy Cat 🐱",
                        "dog" to "Cute Dog 🐶"
                    )

                    mascotOptions.forEach { (value, label) ->
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 4.dp)
                        ) {
                            RadioButton(
                                selected = mascotType == value,
                                onClick = {
                                    TimerService.setMascotType(context, value)
                                    onSettingsSaved()
                                },
                                colors = RadioButtonDefaults.colors(
                                    selectedColor = Color(0xFFFCD34D),
                                    unselectedColor = Color(0x66FFFFFF)
                                )
                            )
                            Text(
                                text = label,
                                color = Color.White,
                                fontSize = 13.sp,
                                modifier = Modifier.padding(start = 8.dp)
                            )
                        }
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
                colors = CardDefaults.cardColors(containerColor = Color(0x14FFFFFF)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth()
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
                            Text("${sessionsPerCycle.toInt()}", color = Color(0xFFA78BFA), fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                        Slider(
                            value = sessionsPerCycle,
                            onValueChange = { sessionsPerCycle = it },
                            onValueChangeFinished = {
                                TimerService.sessionsPerCycle.value = sessionsPerCycle.toInt()
                                val editor = context.getSharedPreferences("GoofyFocusPrefs", Context.MODE_PRIVATE).edit()
                                editor.putInt("SESSIONS_PER_CYCLE", sessionsPerCycle.toInt()).apply()
                                onSettingsSaved()
                            },
                            valueRange = 2f..8f,
                            steps = 5,
                            colors = SliderDefaults.colors(
                                thumbColor = Color(0xFFA78BFA),
                                activeTrackColor = Color(0xFFA78BFA),
                                inactiveTrackColor = Color(0x33FFFFFF)
                            )
                        )
                    }

                    HorizontalDivider(color = Color(0x1AFFFFFF))

                    // Flow Mode Selection (Auto-saves on click)
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Break Flow Strategy", color = Color.White, fontSize = 14.sp)
                        
                        val options = listOf(
                            "auto" to "Auto-Cycling (25/5/25/5/25/15)",
                            "always_short" to "Always Short Breaks",
                            "always_long" to "Always Long Breaks"
                        )

                        options.forEach { (value, label) ->
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 4.dp)
                            ) {
                                RadioButton(
                                    selected = selectedFlow == value,
                                    onClick = {
                                        selectedFlow = value
                                        TimerService.updateSettings(context, workMins.toInt(), shortMins.toInt(), longMins.toInt(), value)
                                        onSettingsSaved()
                                    },
                                    colors = RadioButtonDefaults.colors(
                                        selectedColor = Color(0xFFA78BFA),
                                        unselectedColor = Color(0x66FFFFFF)
                                    )
                                )
                                Text(
                                    text = label,
                                    color = Color.White,
                                    fontSize = 13.sp,
                                    modifier = Modifier.padding(start = 8.dp)
                                )
                            }
                        }
                    }
                }
            }

            // PC Version Promotion Card
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0x0C3B82F6)), // Subtle translucent blue
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth()
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
                colors = CardDefaults.cardColors(containerColor = Color(0x14FFFFFF)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text("How is your experience with GoofyFocus?", color = Color.White, fontSize = 13.sp)
                    
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        for (i in 1..5) {
                            Icon(
                                imageVector = Icons.Filled.Star,
                                contentDescription = "Star $i",
                                tint = if (i <= rating) Color(0xFFFB7185) else Color(0x33FFFFFF),
                                modifier = Modifier
                                    .size(32.dp)
                                    .clickable { rating = i }
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
                colors = CardDefaults.cardColors(containerColor = Color(0x14FFFFFF)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth()
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
                onClick = { handleBack() },
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

private suspend fun sendFeedbackToSupabase(rating: Int, message: String): Boolean {
    return withContext(Dispatchers.IO) {
        try {
            val url = URL("https://nqshkkzrnsafnfvujanr.supabase.co/rest/v1/feedback")
            val conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
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
            conn.disconnect()
            responseCode in 200..299
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }
}
