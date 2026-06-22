package com.example.goofyfocus.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.*
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.goofyfocus.TimerService
import kotlinx.coroutines.delay
import kotlin.math.sin

@Composable
fun MascotWithBubble(
    isRunning: Boolean,
    currentPhase: String,
    modifier: Modifier = Modifier
) {
    var bubbleText by remember { mutableStateOf("") }
    var isBubbleVisible by remember { mutableStateOf(false) }
    val mascotType by TimerService.mascotType.collectAsState()

    // Custom messages
    val focusMessages = listOf(
        "Let's focus together! ⏳",
        "Keep going, you're doing great! 💪",
        "Block out distractions! 🚫",
        "One step at a time! 🚶",
        "Stay goofy, stay focused! 😜"
    )
    val breakMessages = listOf(
        "Time to rest, stretch a bit! ☕",
        "Drink some water! 💧",
        "Look away from the screen! 👀",
        "Take a deep breath. 🧘",
        "Rest is part of the work! 😴"
    )
    val idleMessages = listOf(
        "Start the timer when you're ready! ▶️",
        "Click Settings to configure durations! ⚙️",
        "I'm ready when you are! 🐾"
    )

    // Trigger bubble briefly on phase changes
    LaunchedEffect(currentPhase, isRunning) {
        if (!isRunning) {
            bubbleText = idleMessages.random()
        } else {
            bubbleText = if (currentPhase == "Work") {
                focusMessages.random()
            } else {
                breakMessages.random()
            }
        }
        isBubbleVisible = true
        delay(4000)
        isBubbleVisible = false
    }

    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
        modifier = modifier
            .fillMaxWidth()
            .padding(16.dp)
    ) {
        // Speech Bubble
        AnimatedVisibility(
            visible = isBubbleVisible,
            enter = fadeIn(animationSpec = tween(300)),
            exit = fadeOut(animationSpec = tween(300))
        ) {
            Box(
                modifier = Modifier
                    .padding(bottom = 12.dp)
                    .width(220.dp)
                    .clip(RoundedCornerShape(16.dp))
                    .background(Color(0xCC201C1F))
                    .border(1.dp, Color(0x33FB7185), RoundedCornerShape(16.dp))
                    .clickable { isBubbleVisible = false }
            ) {
                Column(
                    modifier = Modifier
                        .padding(horizontal = 16.dp, vertical = 10.dp)
                        .fillMaxWidth(),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = bubbleText,
                        color = Color.White,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Medium,
                        textAlign = TextAlign.Center
                    )
                }
            }
        }

        // Procedural Mascot (Cat vs Dog)
        ProceduralMascot(
            type = mascotType,
            isActive = isRunning,
            onClick = {
                bubbleText = if (!isRunning) {
                    idleMessages.random()
                } else if (currentPhase == "Work") {
                    focusMessages.random()
                } else {
                    breakMessages.random()
                }
                isBubbleVisible = true
            },
            modifier = Modifier.size(100.dp)
        )
    }
}

@Composable
fun ProceduralMascot(
    type: String,
    isActive: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    // Breathing scale animation
    val infiniteTransition = rememberInfiniteTransition(label = "mascot_breathing")
    val animFrame by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 6.28f, // 2 * PI
        animationSpec = infiniteRepeatable(
            animation = tween(2000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "mascot_breathing"
    )

    // Calculate breathing scale factor
    val scale = 1.0f + 0.03f * sin(animFrame)

    // Blinking eye state
    var isBlinking by remember { mutableStateOf(false) }
    LaunchedEffect(isActive) {
        if (isActive) {
            while (true) {
                delay(kotlin.random.Random.nextLong(2500, 5000))
                isBlinking = true
                delay(120)
                isBlinking = false
            }
        }
    }

    Canvas(
        modifier = modifier
            .graphicsLayer(scaleX = scale, scaleY = scale)
            .clickable(onClick = onClick)
    ) {
        val w = size.width
        val h = size.height
        val cx = w / 2
        val cy = h / 2
        val r = (minOf(w, h) / 2) - 4f

        if (type == "cat") {
            // ── DRAW CAT MASCOT ──
            val bodyBrush = if (isActive) {
                Brush.linearGradient(
                    colors = listOf(Color(0xFFFCD34D), Color(0xFFF59E0B)),
                    start = Offset(cx - r, cy - r),
                    end = Offset(cx + r, cy + r)
                )
            } else {
                Brush.linearGradient(
                    colors = listOf(Color(0xFF94A3B8), Color(0xFF475569)),
                    start = Offset(cx - r, cy - r),
                    end = Offset(cx + r, cy + r)
                )
            }

            // Body
            drawCircle(brush = bodyBrush, radius = r, center = Offset(cx, cy))

            // Left Ear
            val leftEarSway = 5f * sin(animFrame)
            val leftEar = Path().apply {
                moveTo(cx - r * 0.8f, cy - r * 0.4f)
                lineTo(cx - r * 0.9f - leftEarSway, cy - r * 1.1f + leftEarSway * 0.5f)
                lineTo(cx - r * 0.3f, cy - r * 0.8f)
                close()
            }
            drawPath(leftEar, brush = bodyBrush)

            // Right Ear
            val rightEarSway = 5f * sin(animFrame + 1.5f)
            val rightEar = Path().apply {
                moveTo(cx + r * 0.8f, cy - r * 0.4f)
                lineTo(cx + r * 0.9f + rightEarSway, cy - r * 1.1f + rightEarSway * 0.5f)
                lineTo(cx + r * 0.3f, cy - r * 0.8f)
                close()
            }
            drawPath(rightEar, brush = bodyBrush)

            val strokeColor = if (isActive) Color.White else Color(0xFF1E293B)
            val strokeWidth = 2.dp.toPx()

            // Eyes
            if (isActive && !isBlinking) {
                drawArc(
                    color = strokeColor,
                    startAngle = 180f,
                    sweepAngle = 180f,
                    useCenter = false,
                    topLeft = Offset(cx - r * 0.5f, cy - r * 0.35f),
                    size = Size(r * 0.3f, r * 0.25f),
                    style = Stroke(width = strokeWidth)
                )
                drawArc(
                    color = strokeColor,
                    startAngle = 180f,
                    sweepAngle = 180f,
                    useCenter = false,
                    topLeft = Offset(cx + r * 0.2f, cy - r * 0.35f),
                    size = Size(r * 0.3f, r * 0.25f),
                    style = Stroke(width = strokeWidth)
                )
                // Blush
                drawOval(
                    color = Color(0x96FB7185),
                    topLeft = Offset(cx - r * 0.65f, cy - r * 0.05f),
                    size = Size(r * 0.25f, r * 0.15f)
                )
                drawOval(
                    color = Color(0x96FB7185),
                    topLeft = Offset(cx + r * 0.4f, cy - r * 0.05f),
                    size = Size(r * 0.25f, r * 0.15f)
                )
            } else if (isActive && isBlinking) {
                // Closed eyes when blinking (winking/happy closed eyes)
                drawLine(
                    color = strokeColor,
                    start = Offset(cx - r * 0.5f, cy - r * 0.2f),
                    end = Offset(cx - r * 0.2f, cy - r * 0.2f),
                    strokeWidth = strokeWidth
                )
                drawLine(
                    color = strokeColor,
                    start = Offset(cx + r * 0.2f, cy - r * 0.2f),
                    end = Offset(cx + r * 0.5f, cy - r * 0.2f),
                    strokeWidth = strokeWidth
                )
            } else {
                drawLine(
                    color = strokeColor,
                    start = Offset(cx - r * 0.5f, cy - r * 0.15f),
                    end = Offset(cx - r * 0.3f, cy - r * 0.3f),
                    strokeWidth = strokeWidth
                )
                drawLine(
                    color = strokeColor,
                    start = Offset(cx + r * 0.5f, cy - r * 0.15f),
                    end = Offset(cx + r * 0.3f, cy - r * 0.3f),
                    strokeWidth = strokeWidth
                )
                // Tear
                drawPath(
                    path = Path().apply {
                        val tx = cx - r * 0.45f
                        val ty = cy + r * 0.1f
                        moveTo(tx, ty)
                        lineTo(tx - 4f, ty + 10f)
                        lineTo(tx + 4f, ty + 10f)
                        close()
                    },
                    color = Color(0xFF60A5FA)
                )
            }

            // Mouth
            if (isActive) {
                drawArc(
                    color = strokeColor,
                    startAngle = 0f,
                    sweepAngle = 180f,
                    useCenter = false,
                    topLeft = Offset(cx - r * 0.15f, cy - r * 0.05f),
                    size = Size(r * 0.3f, r * 0.25f),
                    style = Stroke(width = strokeWidth)
                )
            } else {
                drawArc(
                    color = strokeColor,
                    startAngle = 180f,
                    sweepAngle = 180f,
                    useCenter = false,
                    topLeft = Offset(cx - r * 0.15f, cy + r * 0.05f),
                    size = Size(r * 0.3f, r * 0.2f),
                    style = Stroke(width = strokeWidth)
                )
            }
        } else {
            // ── DRAW DOG MASCOT ──
            val bodyBrush = if (isActive) {
                // Warm Brown gradient
                Brush.linearGradient(
                    colors = listOf(Color(0xFFF59E0B), Color(0xFFB45309)),
                    start = Offset(cx - r, cy - r),
                    end = Offset(cx + r, cy + r)
                )
            } else {
                // Slate/Dark gradient
                Brush.linearGradient(
                    colors = listOf(Color(0xFF64748B), Color(0xFF334155)),
                    start = Offset(cx - r, cy - r),
                    end = Offset(cx + r, cy + r)
                )
            }

            // Body
            drawCircle(brush = bodyBrush, radius = r, center = Offset(cx, cy))

            // Left Floppy Ear
            val leftEarSway = 4f * sin(animFrame)
            val leftEar = Path().apply {
                moveTo(cx - r * 0.7f, cy - r * 0.3f)
                cubicTo(
                    cx - r * 1.1f - leftEarSway, cy - r * 0.2f,
                    cx - r * 1.0f - leftEarSway, cy + r * 0.5f,
                    cx - r * 0.6f, cy + r * 0.3f
                )
                close()
            }
            drawPath(leftEar, brush = bodyBrush)

            // Right Floppy Ear
            val rightEarSway = 4f * sin(animFrame + 1.5f)
            val rightEar = Path().apply {
                moveTo(cx + r * 0.7f, cy - r * 0.3f)
                cubicTo(
                    cx + r * 1.1f + rightEarSway, cy - r * 0.2f,
                    cx + r * 1.0f + rightEarSway, cy + r * 0.5f,
                    cx + r * 0.6f, cy + r * 0.3f
                )
                close()
            }
            drawPath(rightEar, brush = bodyBrush)

            // Cream Snout / Muzzle
            drawOval(
                color = Color(0xFFFEF3C7), // Soft cream
                topLeft = Offset(cx - r * 0.25f, cy - r * 0.05f),
                size = Size(r * 0.5f, r * 0.4f)
            )

            val strokeColor = if (isActive) Color(0xFF1E293B) else Color(0xFF0F172A)
            val strokeWidth = 2.dp.toPx()

            // Nose
            drawCircle(
                color = Color(0xFF0F172A),
                radius = r * 0.09f,
                center = Offset(cx, cy + r * 0.05f)
            )

            // Eyes
            if (isActive && !isBlinking) {
                // Smiling/Active eyes (small black circles/arcs)
                drawArc(
                    color = Color(0xFF0F172A),
                    startAngle = 180f,
                    sweepAngle = 180f,
                    useCenter = false,
                    topLeft = Offset(cx - r * 0.45f, cy - r * 0.3f),
                    size = Size(r * 0.2f, r * 0.15f),
                    style = Stroke(width = strokeWidth + 1f)
                )
                drawArc(
                    color = Color(0xFF0F172A),
                    startAngle = 180f,
                    sweepAngle = 180f,
                    useCenter = false,
                    topLeft = Offset(cx + r * 0.25f, cy - r * 0.3f),
                    size = Size(r * 0.2f, r * 0.15f),
                    style = Stroke(width = strokeWidth + 1f)
                )
                
                // Active: tongue sticks out
                drawOval(
                    color = Color(0xFFF43F5E), // Pink tongue
                    topLeft = Offset(cx - r * 0.08f, cy + r * 0.18f),
                    size = Size(r * 0.16f, r * 0.22f)
                )
            } else if (isActive && isBlinking) {
                // Dog blinking closed eyes
                drawLine(
                    color = Color(0xFF0F172A),
                    start = Offset(cx - r * 0.45f, cy - r * 0.2f),
                    end = Offset(cx - r * 0.25f, cy - r * 0.2f),
                    strokeWidth = strokeWidth
                )
                drawLine(
                    color = Color(0xFF0F172A),
                    start = Offset(cx + r * 0.25f, cy - r * 0.2f),
                    end = Offset(cx + r * 0.45f, cy - r * 0.2f),
                    strokeWidth = strokeWidth
                )
            } else {
                // Closed/Sleeping eyes (horizontal/angled sleep lines)
                drawLine(
                    color = Color(0xFFCBD5E1),
                    start = Offset(cx - r * 0.45f, cy - r * 0.2f),
                    end = Offset(cx - r * 0.25f, cy - r * 0.2f),
                    strokeWidth = strokeWidth
                )
                drawLine(
                    color = Color(0xFFCBD5E1),
                    start = Offset(cx + r * 0.25f, cy - r * 0.2f),
                    end = Offset(cx + r * 0.45f, cy - r * 0.2f),
                    strokeWidth = strokeWidth
                )
                
                // Sleep tear
                drawPath(
                    path = Path().apply {
                        val tx = cx + r * 0.3f
                        val ty = cy + r * 0.05f
                        moveTo(tx, ty)
                        lineTo(tx - 3f, ty + 7f)
                        lineTo(tx + 3f, ty + 7f)
                        close()
                    },
                    color = Color(0xFF60A5FA)
                )
            }
        }
    }
}
