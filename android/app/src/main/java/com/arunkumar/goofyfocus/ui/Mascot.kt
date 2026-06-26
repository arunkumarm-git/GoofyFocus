package com.arunkumar.goofyfocus.ui

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
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.platform.LocalContext
import com.arunkumar.goofyfocus.TimerService
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.sin
import kotlin.math.cos


enum class MascotExpression {
    IDLE,
    FOCUSED,
    PAUSED,
    CELEBRATING,
    SLEEPING
}

data class MascotSpark(
    val id: Int,
    val x: Float,
    val y: Float,
    val vx: Float,
    val vy: Float,
    val color: Color,
    val maxLife: Int,
    var life: Int,
    val type: Int // 0: Star, 1: Heart, 2: Dot, 3: Zzz
)

@Composable
fun MascotWithBubble(
    isRunning: Boolean,
    currentPhase: String,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    var bubbleText by remember { mutableStateOf("") }
    var isBubbleVisible by remember { mutableStateOf(false) }
    val mascotType by TimerService.mascotType.collectAsState()

    // Determine the base expression from active timer phase
    var activeExpression by remember(isRunning, currentPhase) {
        mutableStateOf(
            if (!isRunning) {
                MascotExpression.PAUSED
            } else if (currentPhase == "Work") {
                MascotExpression.FOCUSED
            } else {
                MascotExpression.SLEEPING
            }
        )
    }

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

        // Procedural Mascot
        ProceduralMascot(
            type = mascotType,
            expression = activeExpression,
            onClick = {
                // Trigger temporary celebrating expression and spring bounce
                coroutineScope.launch {
                    activeExpression = MascotExpression.CELEBRATING
                    delay(1500)
                    activeExpression = if (!isRunning) {
                        MascotExpression.PAUSED
                    } else if (currentPhase == "Work") {
                        MascotExpression.FOCUSED
                    } else {
                        MascotExpression.SLEEPING
                    }
                }

                // Focus XP tap bonus logic
                val now = System.currentTimeMillis()
                val cooldown = 30000L
                val earnedXp = if (now - TimerService.lastXpClickTime > cooldown) {
                    TimerService.lastXpClickTime = now
                    TimerService.addXp(context, 1)
                    true
                } else {
                    false
                }

                bubbleText = if (earnedXp) {
                    listOf(
                        "Woohoo! +1 XP! Keep going! 🌟",
                        "Thanks for the tap! Focus power +1! ⚡",
                        "A little boost of energy! +1 XP! 🔋"
                    ).random()
                } else {
                    if (!isRunning) {
                        idleMessages.random()
                    } else if (currentPhase == "Work") {
                        focusMessages.random()
                    } else {
                        breakMessages.random()
                    }
                }
                isBubbleVisible = true
            },
            modifier = Modifier.size(110.dp)
        )
    }
}

@Composable
fun ProceduralMascot(
    type: String,
    expression: MascotExpression,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val coroutineScope = rememberCoroutineScope()
    
    // Physical bounce scale state
    var isTapped by remember { mutableStateOf(false) }
    val bounceScale by animateFloatAsState(
        targetValue = if (isTapped) 1.25f else 1.0f,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioHighBouncy,
            stiffness = Spring.StiffnessLow
        ),
        label = "mascot_bounce"
    )

    // Spin/Wobble rotation state
    var tapRotationTarget by remember { mutableStateOf(0f) }
    val rotationAnim by animateFloatAsState(
        targetValue = tapRotationTarget,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessLow
        ),
        label = "mascot_rotation"
    )

    // Random ear twitch offsets
    var leftEarTwitch by remember { mutableStateOf(0f) }
    var rightEarTwitch by remember { mutableStateOf(0f) }
    LaunchedEffect(Unit) {
        while (true) {
            delay(kotlin.random.Random.nextLong(3000, 7000))
            if (kotlin.random.Random.nextBoolean()) {
                leftEarTwitch = -12f
                delay(100)
                leftEarTwitch = 8f
                delay(80)
                leftEarTwitch = 0f
            } else {
                rightEarTwitch = 12f
                delay(100)
                rightEarTwitch = -8f
                delay(80)
                rightEarTwitch = 0f
            }
        }
    }
    
    // Spark list for the local particle engine
    val sparks = remember { mutableStateListOf<MascotSpark>() }
    var sparkIdCounter by remember { mutableIntStateOf(0) }
    
    // Continuous breathing animation
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
    val breathingScale = 1.0f + 0.03f * sin(animFrame)
    val scale = bounceScale * breathingScale

    // Blinking eye state
    var isBlinking by remember { mutableStateOf(false) }
    LaunchedEffect(expression) {
        if (expression != MascotExpression.SLEEPING) {
            while (true) {
                delay(kotlin.random.Random.nextLong(2500, 5000))
                isBlinking = true
                delay(120)
                isBlinking = false
            }
        }
    }

    // Spawn Zzz particles periodically if sleeping
    LaunchedEffect(expression) {
        if (expression == MascotExpression.SLEEPING || expression == MascotExpression.PAUSED) {
            while (true) {
                delay(1500)
                // Spawn a Zzz particle at the top-right of the mascot
                sparks.add(
                    MascotSpark(
                        id = sparkIdCounter++,
                        x = 70f, // relative to a 100x100 box
                        y = 30f,
                        vx = kotlin.random.Random.nextFloat() * 0.4f + 0.2f,
                        vy = -(kotlin.random.Random.nextFloat() * 0.5f + 0.4f),
                        color = Color(0xFFA78BFA),
                        maxLife = 120,
                        life = 120,
                        type = 3 // Zzz
                    )
                )
            }
        }
    }

    // Spark physical animation tick
    LaunchedEffect(sparks.size) {
        if (sparks.isNotEmpty()) {
            while (sparks.isNotEmpty()) {
                delay(16) // ~60 FPS
                val toRemove = mutableListOf<MascotSpark>()
                for (i in sparks.indices) {
                    val s = sparks[i]
                    s.life -= 1
                    if (s.life <= 0) {
                        toRemove.add(s)
                    } else {
                        // Move particle
                        val newVy = if (s.type == 3) s.vy else s.vy + 0.03f // Less gravity for Zzz
                        val newVx = if (s.type == 3) s.vx + 0.02f * sin(s.life * 0.1f) else s.vx // Sway for Zzz
                        sparks[i] = s.copy(
                            x = s.x + newVx,
                            y = s.y + newVy,
                            vx = newVx,
                            vy = newVy
                        )
                    }
                }
                sparks.removeAll(toRemove)
            }
        }
    }

    Canvas(
        modifier = modifier
            .graphicsLayer(
                scaleX = scale,
                scaleY = scale,
                rotationZ = rotationAnim
            )
            .clickable {
                // Trigger physical bounce and barrel spin animation
                coroutineScope.launch {
                    isTapped = true
                    tapRotationTarget += 360f
                    delay(80)
                    isTapped = false
                }
                
                // Spawn 12 spark particles including music notes & sparkles
                val colors = listOf(Color(0xFFFB7185), Color(0xFFA78BFA), Color(0xFFFCD34D), Color(0xFF60A5FA))
                val particleTypes = listOf(0, 1, 2, 4, 5) // Star, Heart, Dot, Music Note, Sparkle
                for (i in 0 until 12) {
                    val angle = (kotlin.random.Random.nextFloat() * 2 * Math.PI).toFloat()
                    val speed = kotlin.random.Random.nextFloat() * 1.5f + 0.5f
                    sparks.add(
                        MascotSpark(
                            id = sparkIdCounter++,
                            x = 50f, // Center of 100x100
                            y = 40f,
                            vx = (cos(angle) * speed),
                            vy = (sin(angle) * speed - 1.0f), // bias upwards
                            color = colors.random(),
                            maxLife = 60,
                            life = 60,
                            type = particleTypes.random()
                        )
                    )
                }

                onClick()
            }
    ) {
        val w = size.width
        val h = size.height
        val cx = w / 2
        val cy = h / 2
        val r = (minOf(w, h) / 2) - 10f // room for objects

        // Helper functions inside DrawScope
        fun drawStar(px: Float, py: Float, radius: Float, color: Color) {
            val path = Path()
            val numPoints = 5
            var angle = -Math.PI / 2
            val step = Math.PI / numPoints
            path.moveTo(
                (px + cos(angle) * radius).toFloat(),
                (py + sin(angle) * radius).toFloat()
            )
            for (i in 0 until numPoints * 2) {
                angle += step
                val rCur = if (i % 2 == 0) radius * 0.4f else radius
                path.lineTo(
                    (px + cos(angle) * rCur).toFloat(),
                    (py + sin(angle) * rCur).toFloat()
                )
            }
            path.close()
            drawPath(path, color)
        }

        fun drawHeart(px: Float, py: Float, size: Float, color: Color) {
            val path = Path().apply {
                val half = size / 2
                moveTo(px, py + size * 0.25f)
                cubicTo(px - half, py - half * 0.8f, px - size, py + size * 0.3f, px, py + size)
                cubicTo(px + size, py + size * 0.3f, px + half, py - half * 0.8f, px, py + size * 0.25f)
                close()
            }
            drawPath(path, color)
        }

        // Draw mascot body base depending on expression
        if (type == "cat") {
            // Draw Cat
            val isActive = (expression == MascotExpression.FOCUSED || expression == MascotExpression.CELEBRATING || expression == MascotExpression.IDLE)
            val bodyBrush = if (isActive) {
                Brush.linearGradient(
                    colors = if (expression == MascotExpression.CELEBRATING) {
                        listOf(Color(0xFFFDA4AF), Color(0xFFF43F5E)) // pink celebration
                    } else {
                        listOf(Color(0xFFFCD34D), Color(0xFFF59E0B)) // warm yellow focus/idle
                    },
                    start = Offset(cx - r, cy - r),
                    end = Offset(cx + r, cy + r)
                )
            } else {
                Brush.linearGradient(
                    colors = listOf(Color(0xFF94A3B8), Color(0xFF475569)), // sleeping/paused slate
                    start = Offset(cx - r, cy - r),
                    end = Offset(cx + r, cy + r)
                )
            }

            // Draw Ears
            val leftEarSway = 5f * sin(animFrame) + leftEarTwitch
            val leftEar = Path().apply {
                moveTo(cx - r * 0.8f, cy - r * 0.4f)
                lineTo(cx - r * 0.9f - leftEarSway, cy - r * 1.1f + leftEarSway * 0.5f)
                lineTo(cx - r * 0.3f, cy - r * 0.8f)
                close()
            }
            drawPath(leftEar, brush = bodyBrush)

            val rightEarSway = 5f * sin(animFrame + 1.5f) + rightEarTwitch
            val rightEar = Path().apply {
                moveTo(cx + r * 0.8f, cy - r * 0.4f)
                lineTo(cx + r * 0.9f + rightEarSway, cy - r * 1.1f + rightEarSway * 0.5f)
                lineTo(cx + r * 0.3f, cy - r * 0.8f)
                close()
            }
            drawPath(rightEar, brush = bodyBrush)

            // Draw Cat Tail (Wagging behind body)
            val tailSway = (if (expression == MascotExpression.CELEBRATING) 25f else 10f) * sin(animFrame * 2f)
            val tailPath = Path().apply {
                moveTo(cx + r * 0.5f, cy + r * 0.6f)
                cubicTo(
                    cx + r * 0.9f + tailSway, cy + r * 0.5f - tailSway * 0.3f,
                    cx + r * 1.2f + tailSway, cy - r * 0.1f + tailSway,
                    cx + r * 1.0f + tailSway * 0.8f, cy - r * 0.4f
                )
            }
            drawPath(
                path = tailPath,
                brush = bodyBrush,
                style = Stroke(width = 8.dp.toPx(), cap = androidx.compose.ui.graphics.StrokeCap.Round)
            )

            // Draw Body Circle
            drawCircle(brush = bodyBrush, radius = r, center = Offset(cx, cy))

            val strokeColor = if (isActive) Color.White else Color(0xFF1E293B)
            val strokeWidth = 2.dp.toPx()

            // Draw Eyes based on Expression
            when (expression) {
                MascotExpression.CELEBRATING -> {
                    // Big star eyes or happy winks
                    drawStar(cx - r * 0.35f, cy - r * 0.2f, r * 0.18f, Color.White)
                    drawStar(cx + r * 0.35f, cy - r * 0.2f, r * 0.18f, Color.White)
                    
                    // Blush
                    drawOval(Color(0xB2F43F5E), Offset(cx - r * 0.65f, cy - r * 0.05f), Size(r * 0.25f, r * 0.15f))
                    drawOval(Color(0xB2F43F5E), Offset(cx + r * 0.4f, cy - r * 0.05f), Size(r * 0.25f, r * 0.15f))
                }
                MascotExpression.FOCUSED -> {
                    // Determined eyes looking down at laptop
                    drawArc(
                        color = strokeColor,
                        startAngle = 0f,
                        sweepAngle = 180f,
                        useCenter = false,
                        topLeft = Offset(cx - r * 0.45f, cy - r * 0.3f),
                        size = Size(r * 0.22f, r * 0.12f),
                        style = Stroke(width = strokeWidth + 1f)
                    )
                    drawArc(
                        color = strokeColor,
                        startAngle = 0f,
                        sweepAngle = 180f,
                        useCenter = false,
                        topLeft = Offset(cx + r * 0.23f, cy - r * 0.3f),
                        size = Size(r * 0.22f, r * 0.12f),
                        style = Stroke(width = strokeWidth + 1f)
                    )
                    // Little focus sweat/spark bead
                    drawCircle(Color(0xFF60A5FA), radius = 3.dp.toPx(), center = Offset(cx - r * 0.55f, cy - r * 0.4f))
                }
                MascotExpression.SLEEPING, MascotExpression.PAUSED -> {
                    // Closed sleeping curved lines
                    drawArc(
                        color = strokeColor,
                        startAngle = 0f,
                        sweepAngle = 180f,
                        useCenter = false,
                        topLeft = Offset(cx - r * 0.45f, cy - r * 0.25f),
                        size = Size(r * 0.2f, r * 0.15f),
                        style = Stroke(width = strokeWidth)
                    )
                    drawArc(
                        color = strokeColor,
                        startAngle = 0f,
                        sweepAngle = 180f,
                        useCenter = false,
                        topLeft = Offset(cx + r * 0.25f, cy - r * 0.25f),
                        size = Size(r * 0.2f, r * 0.15f),
                        style = Stroke(width = strokeWidth)
                    )
                }
                MascotExpression.IDLE -> {
                    if (isBlinking) {
                        drawLine(strokeColor, Offset(cx - r * 0.45f, cy - r * 0.2f), Offset(cx - r * 0.25f, cy - r * 0.2f), strokeWidth)
                        drawLine(strokeColor, Offset(cx + r * 0.25f, cy - r * 0.2f), Offset(cx + r * 0.45f, cy - r * 0.2f), strokeWidth)
                    } else {
                        // Normal happy open arches
                        drawArc(
                            color = strokeColor,
                            startAngle = 180f,
                            sweepAngle = 180f,
                            useCenter = false,
                            topLeft = Offset(cx - r * 0.45f, cy - r * 0.35f),
                            size = Size(r * 0.25f, r * 0.2f),
                            style = Stroke(width = strokeWidth)
                        )
                        drawArc(
                            color = strokeColor,
                            startAngle = 180f,
                            sweepAngle = 180f,
                            useCenter = false,
                            topLeft = Offset(cx + r * 0.2f, cy - r * 0.35f),
                            size = Size(r * 0.25f, r * 0.2f),
                            style = Stroke(width = strokeWidth)
                        )
                        // Soft pink cheeks
                        drawOval(Color(0x7FBC5F6B), Offset(cx - r * 0.65f, cy - r * 0.05f), Size(r * 0.22f, r * 0.12f))
                        drawOval(Color(0x7FBC5F6B), Offset(cx + r * 0.43f, cy - r * 0.05f), Size(r * 0.22f, r * 0.12f))
                    }
                }
            }

            // Draw Mouth
            if (expression == MascotExpression.CELEBRATING) {
                // Wide open happy mouth
                val mouthPath = Path().apply {
                    moveTo(cx - r * 0.15f, cy + r * 0.02f)
                    quadraticTo(cx, cy + r * 0.25f, cx + r * 0.15f, cy + r * 0.02f)
                    close()
                }
                drawPath(mouthPath, Color(0xFFF43F5E))
            } else if (expression == MascotExpression.SLEEPING || expression == MascotExpression.PAUSED) {
                // Small round 'O' mouth or flat smile
                drawCircle(strokeColor, radius = r * 0.05f, center = Offset(cx, cy + r * 0.1f))
            } else {
                // Normal smile
                drawArc(
                    color = strokeColor,
                    startAngle = 0f,
                    sweepAngle = 180f,
                    useCenter = false,
                    topLeft = Offset(cx - r * 0.12f, cy - r * 0.02f),
                    size = Size(r * 0.24f, r * 0.2f),
                    style = Stroke(width = strokeWidth)
                )
            }

            // Draw Focus-Work details (Laptop)
            if (expression == MascotExpression.FOCUSED) {
                // Draw a mini glowing blue laptop at the bottom of the cat
                val laptopW = r * 0.8f
                val laptopH = r * 0.5f
                val lx = cx - laptopW / 2
                val ly = cy + r * 0.35f
                
                // Screen (Blue glowing rect)
                drawRoundRect(
                    color = Color(0xFF1E293B),
                    topLeft = Offset(lx, ly),
                    size = Size(laptopW, laptopH * 0.7f),
                    cornerRadius = CornerRadius(4.dp.toPx(), 4.dp.toPx())
                )
                drawRoundRect(
                    color = Color(0x6660A5FA), // Cyan/Blue glow screen
                    topLeft = Offset(lx + 2.dp.toPx(), ly + 2.dp.toPx()),
                    size = Size(laptopW - 4.dp.toPx(), laptopH * 0.7f - 4.dp.toPx()),
                    cornerRadius = CornerRadius(2.dp.toPx(), 2.dp.toPx())
                )
                
                // Keyboard Base
                val base = Path().apply {
                    moveTo(lx - 2.dp.toPx(), ly + laptopH * 0.7f)
                    lineTo(lx + laptopW + 2.dp.toPx(), ly + laptopH * 0.7f)
                    lineTo(lx + laptopW + 10.dp.toPx(), ly + laptopH)
                    lineTo(lx - 10.dp.toPx(), ly + laptopH)
                    close()
                }
                drawPath(base, Color(0xFF475569))
            }

        } else {
            // Draw Dog Mascot
            val isActive = (expression == MascotExpression.FOCUSED || expression == MascotExpression.CELEBRATING || expression == MascotExpression.IDLE)
            val bodyBrush = if (isActive) {
                Brush.linearGradient(
                    colors = if (expression == MascotExpression.CELEBRATING) {
                        listOf(Color(0xFFFCA5A5), Color(0xFFDC2626)) // reddish dog celebration
                    } else {
                        listOf(Color(0xFFF59E0B), Color(0xFFB45309)) // warm brown dog focus/idle
                    },
                    start = Offset(cx - r, cy - r),
                    end = Offset(cx + r, cy + r)
                )
            } else {
                Brush.linearGradient(
                    colors = listOf(Color(0xFF64748B), Color(0xFF334155)), // sleeping/paused dog
                    start = Offset(cx - r, cy - r),
                    end = Offset(cx + r, cy + r)
                )
            }

            // Left Floppy Ear
            val leftEarSway = 4f * sin(animFrame) + leftEarTwitch
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
            val rightEarSway = 4f * sin(animFrame + 1.5f) + rightEarTwitch
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

            // Draw Dog Tail (Wagging behind body)
            val tailSway = (if (expression == MascotExpression.CELEBRATING) 30f else 12f) * sin(animFrame * 2.5f)
            val tailPath = Path().apply {
                moveTo(cx - r * 0.5f, cy + r * 0.6f)
                cubicTo(
                    cx - r * 0.9f - tailSway, cy + r * 0.5f - tailSway * 0.3f,
                    cx - r * 1.2f - tailSway, cy - r * 0.1f + tailSway,
                    cx - r * 1.0f - tailSway * 0.8f, cy - r * 0.4f
                )
            }
            drawPath(
                path = tailPath,
                brush = bodyBrush,
                style = Stroke(width = 10.dp.toPx(), cap = androidx.compose.ui.graphics.StrokeCap.Round)
            )

            // Dog Body Circle
            drawCircle(brush = bodyBrush, radius = r, center = Offset(cx, cy))

            // Cream Snout
            drawOval(
                color = Color(0xFFFEF3C7),
                topLeft = Offset(cx - r * 0.25f, cy - r * 0.05f),
                size = Size(r * 0.5f, r * 0.4f)
            )

            // Nose
            drawCircle(
                color = Color(0xFF0F172A),
                radius = r * 0.09f,
                center = Offset(cx, cy + r * 0.05f)
            )

            val strokeColor = if (isActive) Color(0xFF1E293B) else Color(0xFF0F172A)
            val strokeWidth = 2.dp.toPx()

            // Draw Eyes based on Expression
            when (expression) {
                MascotExpression.CELEBRATING -> {
                    // Happy wide-open eyes with stars
                    drawStar(cx - r * 0.35f, cy - r * 0.2f, r * 0.15f, Color(0xFF0F172A))
                    drawStar(cx + r * 0.35f, cy - r * 0.2f, r * 0.15f, Color(0xFF0F172A))
                    
                    // Blush
                    drawOval(Color(0xB2EF4444), Offset(cx - r * 0.55f, cy - r * 0.05f), Size(r * 0.25f, r * 0.15f))
                    drawOval(Color(0xB2EF4444), Offset(cx + r * 0.3f, cy - r * 0.05f), Size(r * 0.25f, r * 0.15f))
                }
                MascotExpression.FOCUSED -> {
                    // Concentrated eyes looking down
                    drawArc(
                        color = Color(0xFF0F172A),
                        startAngle = 0f,
                        sweepAngle = 180f,
                        useCenter = false,
                        topLeft = Offset(cx - r * 0.4f, cy - r * 0.25f),
                        size = Size(r * 0.16f, r * 0.1f),
                        style = Stroke(width = strokeWidth + 1f)
                    )
                    drawArc(
                        color = Color(0xFF0F172A),
                        startAngle = 0f,
                        sweepAngle = 180f,
                        useCenter = false,
                        topLeft = Offset(cx + r * 0.24f, cy - r * 0.25f),
                        size = Size(r * 0.16f, r * 0.1f),
                        style = Stroke(width = strokeWidth + 1f)
                    )
                }
                MascotExpression.SLEEPING, MascotExpression.PAUSED -> {
                    // Cute closed sleeping lines
                    drawLine(Color(0xFF94A3B8), Offset(cx - r * 0.4f, cy - r * 0.2f), Offset(cx - r * 0.2f, cy - r * 0.2f), strokeWidth)
                    drawLine(Color(0xFF94A3B8), Offset(cx + r * 0.2f, cy - r * 0.2f), Offset(cx + r * 0.4f, cy - r * 0.2f), strokeWidth)
                }
                MascotExpression.IDLE -> {
                    if (isBlinking) {
                        drawLine(Color(0xFF0F172A), Offset(cx - r * 0.4f, cy - r * 0.2f), Offset(cx - r * 0.2f, cy - r * 0.2f), strokeWidth)
                        drawLine(Color(0xFF0F172A), Offset(cx + r * 0.2f, cy - r * 0.2f), Offset(cx + r * 0.4f, cy - r * 0.2f), strokeWidth)
                    } else {
                        // Smiling eyes
                        drawArc(
                            color = Color(0xFF0F172A),
                            startAngle = 180f,
                            sweepAngle = 180f,
                            useCenter = false,
                            topLeft = Offset(cx - r * 0.4f, cy - r * 0.3f),
                            size = Size(r * 0.18f, r * 0.12f),
                            style = Stroke(width = strokeWidth + 1f)
                        )
                        drawArc(
                            color = Color(0xFF0F172A),
                            startAngle = 180f,
                            sweepAngle = 180f,
                            useCenter = false,
                            topLeft = Offset(cx + r * 0.22f, cy - r * 0.3f),
                            size = Size(r * 0.18f, r * 0.12f),
                            style = Stroke(width = strokeWidth + 1f)
                        )
                    }
                }
            }

            // Mouth
            if (expression == MascotExpression.CELEBRATING || expression == MascotExpression.IDLE) {
                // Tongue sticks out
                drawOval(
                    color = Color(0xFFF43F5E),
                    topLeft = Offset(cx - r * 0.08f, cy + r * 0.18f),
                    size = Size(r * 0.16f, r * 0.22f)
                )
            } else if (expression == MascotExpression.SLEEPING || expression == MascotExpression.PAUSED) {
                // Soft flat snout details
            } else {
                // Small flat line mouth
                drawLine(Color(0xFF0F172A), Offset(cx - r * 0.08f, cy + r * 0.2f), Offset(cx + r * 0.08f, cy + r * 0.2f), strokeWidth)
            }

            // Draw Focus-Work details (Study Book)
            if (expression == MascotExpression.FOCUSED) {
                val bookW = r * 0.7f
                val bookH = r * 0.4f
                val bx = cx - bookW / 2
                val by = cy + r * 0.35f
                
                // Draw open pages (procedural cream rectangles)
                drawRoundRect(
                    color = Color(0xFFFEF3C7), // cream page background
                    topLeft = Offset(bx, by),
                    size = Size(bookW, bookH),
                    cornerRadius = CornerRadius(2.dp.toPx(), 2.dp.toPx())
                )
                // Draw spine line
                drawLine(
                    color = Color(0xFFD97706),
                    start = Offset(cx, by),
                    end = Offset(cx, by + bookH),
                    strokeWidth = 2.dp.toPx()
                )
                // Draw placeholder page text lines
                drawLine(Color(0xFFCBD5E1), Offset(bx + 4.dp.toPx(), by + 4.dp.toPx()), Offset(cx - 4.dp.toPx(), by + 4.dp.toPx()), 1.dp.toPx())
                drawLine(Color(0xFFCBD5E1), Offset(bx + 4.dp.toPx(), by + 8.dp.toPx()), Offset(cx - 4.dp.toPx(), by + 8.dp.toPx()), 1.dp.toPx())
                drawLine(Color(0xFFCBD5E1), Offset(cx + 4.dp.toPx(), by + 4.dp.toPx()), Offset(bx + bookW - 4.dp.toPx(), by + 4.dp.toPx()), 1.dp.toPx())
                drawLine(Color(0xFFCBD5E1), Offset(cx + 4.dp.toPx(), by + 8.dp.toPx()), Offset(bx + bookW - 4.dp.toPx(), by + 8.dp.toPx()), 1.dp.toPx())
            }
        }

        // Draw active Particle Sparks from local engine
        sparks.forEach { s ->
            // Map relative 100x100 coord to actual canvas size
            val sx = (s.x / 100f) * w
            val sy = (s.y / 100f) * h
            val sizePx = 6.dp.toPx() * (s.life.toFloat() / s.maxLife.toFloat())
            val alphaColor = s.color.copy(alpha = s.life.toFloat() / s.maxLife.toFloat())

            when (s.type) {
                0 -> drawStar(sx, sy, sizePx, alphaColor)
                1 -> drawHeart(sx, sy, sizePx, alphaColor)
                2 -> drawCircle(alphaColor, radius = sizePx * 0.7f, center = Offset(sx, sy))
                3 -> {
                    // Draw Zzz text
                    val sizeSp = (10 + 6 * (s.life.toFloat() / s.maxLife.toFloat())).sp
                    val zW = sizePx * 1.5f
                    val zH = sizePx * 1.8f
                    val zColor = alphaColor.copy(alpha = s.life.toFloat() / s.maxLife.toFloat() * 0.7f)
                    val zPath = Path().apply {
                        moveTo(sx - zW / 2, sy - zH / 2)
                        lineTo(sx + zW / 2, sy - zH / 2)
                        lineTo(sx - zW / 2, sy + zH / 2)
                        lineTo(sx + zW / 2, sy + zH / 2)
                    }
                    drawPath(zPath, color = zColor, style = Stroke(width = 1.5.dp.toPx()))
                }
                4 -> {
                    // Draw Music Note
                    val stemW = 1.5.dp.toPx()
                    val headR = sizePx * 0.4f
                    drawCircle(alphaColor, radius = headR, center = Offset(sx - sizePx * 0.2f, sy + sizePx * 0.3f))
                    drawLine(
                        color = alphaColor,
                        start = Offset(sx - sizePx * 0.2f + headR, sy + sizePx * 0.3f),
                        end = Offset(sx - sizePx * 0.2f + headR, sy - sizePx * 0.4f),
                        strokeWidth = stemW
                    )
                    drawLine(
                        color = alphaColor,
                        start = Offset(sx - sizePx * 0.2f + headR, sy - sizePx * 0.4f),
                        end = Offset(sx + sizePx * 0.3f, sy - sizePx * 0.2f),
                        strokeWidth = stemW
                    )
                }
                5 -> {
                    // Draw Sparkle (Procedural 4-point sparkle)
                    val sparklePath = Path().apply {
                        moveTo(sx, sy - sizePx)
                        quadraticTo(sx, sy, sx + sizePx, sy)
                        quadraticTo(sx, sy, sx, sy + sizePx)
                        quadraticTo(sx, sy, sx - sizePx, sy)
                        quadraticTo(sx, sy, sx, sy - sizePx)
                        close()
                    }
                    drawPath(sparklePath, alphaColor)
                }
            }
        }
    }
}

