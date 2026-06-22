package com.example.goofyfocus.ui.main

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation3.runtime.NavKey
import com.example.goofyfocus.Settings
import com.example.goofyfocus.TimerService
import com.example.goofyfocus.ui.MascotWithBubble
import kotlin.math.sin

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    onItemClick: (NavKey) -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    
    // Collect active timer states from Foreground Service
    val remainingSecs by TimerService.remainingSecs.collectAsStateWithLifecycle()
    val totalSecs by TimerService.totalSecs.collectAsStateWithLifecycle()
    val phase by TimerService.currentPhase.collectAsStateWithLifecycle()
    val isRunning by TimerService.isRunning.collectAsStateWithLifecycle()
    val completedSessions by TimerService.sessionsCompleted.collectAsStateWithLifecycle()
    val sessionsPerCycle by TimerService.sessionsPerCycle.collectAsStateWithLifecycle()

    // Formatting time
    val minutes = remainingSecs / 60
    val seconds = remainingSecs % 60
    val timeString = String.format("%02d:%02d", minutes, seconds)

    // Calculate progress fraction
    val progress = if (totalSecs > 0) {
        remainingSecs.toFloat() / totalSecs.toFloat()
    } else {
        1.0f
    }

    // Smoothly animate progress sweep for premium transitions
    val animatedProgress by animateFloatAsState(
        targetValue = progress,
        animationSpec = tween(durationMillis = 500, easing = LinearOutSlowInEasing),
        label = "timer_progress"
    )

    // Colors
    val accentPink = Color(0xFFFB7185)
    val accentPurple = Color(0xFFA78BFA)

    // Smooth morphing colors for phase indicator
    val phaseColor by animateColorAsState(
        targetValue = if (phase == "Work") accentPink else accentPurple,
        animationSpec = tween(durationMillis = 500),
        label = "phase_text_color"
    )
    val cardBgColor by animateColorAsState(
        targetValue = if (phase == "Work") Color(0x1EFB7185) else Color(0x1EA78BFA),
        animationSpec = tween(durationMillis = 500),
        label = "phase_card_color"
    )
    
    // Background gradient breathing animation
    val infiniteTransition = rememberInfiniteTransition(label = "bg_glow")
    val pulse by infiniteTransition.animateFloat(
        initialValue = 0.9f,
        targetValue = 1.1f,
        animationSpec = infiniteRepeatable(
            animation = tween(5000, easing = EaseInOutSine),
            repeatMode = RepeatMode.Reverse
        ),
        label = "bg_glow"
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("GoofyFocus ⏳", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 20.sp) },
                actions = {
                    IconButton(onClick = { onItemClick(Settings) }) {
                        Icon(
                            imageVector = Icons.Default.Settings,
                            contentDescription = "Settings",
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
        Box(
            modifier = Modifier
                .padding(innerPadding)
                .fillMaxSize()
        ) {
            // Ambient animated back-glow
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .blur(100.dp)
            ) {
                Canvas(modifier = Modifier.fillMaxSize()) {
                    drawCircle(
                        brush = Brush.radialGradient(
                            colors = listOf(Color(0x1EFB7185), Color.Transparent)
                        ),
                        radius = size.minDimension * 0.5f * pulse,
                        center = Offset(size.width / 2, size.height * 0.4f)
                    )
                }
            }

            // Foreground Layout
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.SpaceBetween
            ) {
                // Phase Indicator Card (morphs background and text colors smoothly)
                Card(
                    colors = CardDefaults.cardColors(containerColor = cardBgColor),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text(
                        text = phase.uppercase(),
                        color = phaseColor,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 2.sp,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp)
                    )
                }

                // 1. Circular Progress Timer
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier.size(240.dp)
                ) {
                    // Draw custom progress ring
                    Canvas(modifier = Modifier.fillMaxSize()) {
                        val strokeWidthPx = 10.dp.toPx()
                        val diameter = size.minDimension - strokeWidthPx
                        val topLeft = Offset(strokeWidthPx / 2, strokeWidthPx / 2)
                        
                        // Background track circle
                        drawCircle(
                            color = Color(0x1AFFFFFF),
                            radius = diameter / 2,
                            center = center,
                            style = Stroke(width = strokeWidthPx)
                        )

                        // Glowing gradient progress arc
                        drawArc(
                            brush = Brush.linearGradient(
                                colors = listOf(accentPink, accentPurple)
                            ),
                            startAngle = -90f,
                            sweepAngle = 360f * animatedProgress,
                            useCenter = false,
                            topLeft = topLeft,
                            size = Size(diameter, diameter),
                            style = Stroke(
                                width = strokeWidthPx,
                                cap = StrokeCap.Round
                            )
                        )
                    }

                    // Inside digital text
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = timeString,
                            color = Color.White,
                            fontSize = 44.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = if (isRunning) "ACTIVE" else "PAUSED",
                            color = Color(0x99FFFFFF),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold,
                            letterSpacing = 1.sp
                        )
                    }
                }

                // 2. Completed Sessions tracker (clearly labeled to avoid swipe-dot confusion)
                SessionProgressTracker(
                    completed = completedSessions % sessionsPerCycle,
                    total = sessionsPerCycle,
                    accentColor = accentPink
                )

                // 3. Mascot Companion
                MascotWithBubble(
                    isRunning = isRunning,
                    currentPhase = phase,
                    modifier = Modifier.height(180.dp)
                )

                // 4. Control Row
                Row(
                    horizontalArrangement = Arrangement.spacedBy(24.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.padding(bottom = 16.dp)
                ) {
                    // Reset Button
                    IconButton(
                        onClick = { TimerService.reset(context) },
                        modifier = Modifier
                            .size(48.dp)
                            .background(Color(0x1AFFFFFF), CircleShape)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Refresh,
                            contentDescription = "Reset",
                            tint = Color.White
                        )
                    }

                    // Play/Pause Pill Button
                    Button(
                        onClick = {
                            if (isRunning) {
                                TimerService.pause(context)
                            } else {
                                TimerService.start(context)
                            }
                        },
                        shape = RoundedCornerShape(24.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = accentPink,
                            contentColor = Color.White
                        ),
                        modifier = Modifier
                            .width(130.dp)
                            .height(48.dp)
                    ) {
                        Text(
                            text = if (isRunning) "Pause" else "Start",
                            fontWeight = FontWeight.Bold,
                            fontSize = 15.sp
                        )
                    }

                    // Skip Button
                    IconButton(
                        onClick = { TimerService.skip(context) },
                        modifier = Modifier
                            .size(48.dp)
                            .background(Color(0x1AFFFFFF), CircleShape)
                    ) {
                        Icon(
                            painter = painterResource(android.R.drawable.ic_media_next),
                            contentDescription = "Skip",
                            tint = Color.White
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun SessionProgressTracker(
    completed: Int,
    total: Int,
    accentColor: Color,
    modifier: Modifier = Modifier
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(6.dp),
        modifier = modifier
    ) {
        Text(
            text = "Session ${completed + 1} of $total",
            color = Color(0xB3FFFFFF),
            fontSize = 11.sp,
            fontWeight = FontWeight.SemiBold,
            letterSpacing = 0.5.sp
        )
        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            for (i in 0 until total) {
                val isCompleted = i < completed
                val isCurrent = i == completed

                Box(
                    modifier = Modifier
                        .size(if (isCurrent) 10.dp else 8.dp)
                        .clip(CircleShape)
                        .background(
                            when {
                                isCompleted -> accentColor
                                isCurrent -> Color.White
                                else -> Color(0x33FFFFFF)
                            }
                        )
                )
            }
        }
    }
}
