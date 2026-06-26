package com.arunkumar.goofyfocus.ui

import android.graphics.ImageDecoder
import android.graphics.drawable.AnimatedImageDrawable
import android.media.MediaPlayer
import android.net.Uri
import android.os.Build
import android.widget.ImageView
import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import com.arunkumar.goofyfocus.TimerService
import kotlin.random.Random

@Composable
fun BreakOverlayScreen(
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val remainingSecs by TimerService.remainingSecs.collectAsState()
    val phase by TimerService.currentPhase.collectAsState()
    val customGifUri by TimerService.customGifUri.collectAsState()
    val mascotType by TimerService.mascotType.collectAsState()

    // Sound state
    var isMuted by remember { mutableStateOf(false) }
    val mediaPlayerState = remember { mutableStateOf<MediaPlayer?>(null) }

    // If phase changes back to Work, automatically dismiss the break screen
    LaunchedEffect(phase) {
        if (phase == "Work") {
            onDismiss()
        }
    }

    // Format remaining time
    val minutes = remainingSecs / 60
    val seconds = remainingSecs % 60
    val timeString = String.format("%02d:%02d", minutes, seconds)

    // Breathing pulse animation for the gradient glow
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val pulseScale by infiniteTransition.animateFloat(
        initialValue = 0.8f,
        targetValue = 1.2f,
        animationSpec = infiniteRepeatable(
            animation = tween(4000, easing = EaseInOutSine),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse"
    )

    // Background particles data
    val particles = remember {
        List(25) {
            ParticleData(
                x = Random.nextFloat(),
                y = Random.nextFloat(),
                size = Random.nextFloat() * 12f + 4f,
                speed = Random.nextFloat() * 0.002f + 0.0005f
            )
        }
    }

    // Animation state for floating particles
    val particleAnim by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(10000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "particles"
    )

    // Resolve break GIF: user selected vs random packaged asset
    val selectedGifPath = remember(customGifUri) {
        if (customGifUri != null) {
            customGifUri
        } else {
            val allGifs = getGifPaths(context, "gifs")
            if (allGifs.isNotEmpty()) {
                allGifs.random()
            } else {
                null
            }
        }
    }

    // Audio playback logic (plays random sound from assets)
    LaunchedEffect(isMuted) {
        if (isMuted) {
            mediaPlayerState.value?.stop()
            mediaPlayerState.value?.release()
            mediaPlayerState.value = null
        } else {
            try {
                val allSounds = getSoundPaths(context, "sounds")
                if (allSounds.isNotEmpty()) {
                    val soundFile = allSounds.random()
                    val afd = context.assets.openFd(soundFile)
                    val mp = MediaPlayer().apply {
                        setDataSource(afd.fileDescriptor, afd.startOffset, afd.length)
                        isLooping = true
                        prepare()
                        start()
                    }
                    mediaPlayerState.value = mp
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    // Clean up MediaPlayer on leave
    DisposableEffect(Unit) {
        onDispose {
            mediaPlayerState.value?.stop()
            mediaPlayerState.value?.release()
            mediaPlayerState.value = null
        }
    }

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFF0F0D0E)), // Deep dark base
        contentAlignment = Alignment.Center
    ) {
        // 1. Animated background gradients (ambient glowing background)
        Box(
            modifier = Modifier
                .fillMaxSize()
                .blur(80.dp)
        ) {
            Canvas(modifier = Modifier.fillMaxSize()) {
                val center = Offset(size.width / 2, size.height / 2)
                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(
                            Color(0x2BFA7185), // Soft accent pink
                            Color.Transparent
                        )
                    ),
                    radius = size.minDimension * 0.6f * pulseScale,
                    center = center
                )
                
                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(
                            Color(0x1EA78BFA), // Soft purple accent
                            Color.Transparent
                        )
                    ),
                    radius = size.minDimension * 0.5f * (2f - pulseScale),
                    center = Offset(center.x + 100f, center.y - 150f)
                )
            }
        }

        // 2. Custom Canvas Particles (Drifting hearts/bubbles effect)
        Canvas(modifier = Modifier.fillMaxSize()) {
            particles.forEach { p ->
                val currentY = (p.y - (particleAnim * p.speed * 200f)) % 1.0f
                val finalY = if (currentY < 0f) currentY + 1.0f else currentY
                
                drawCircle(
                    color = Color(0x33FB7185),
                    radius = p.size,
                    center = Offset(p.x * size.width, finalY * size.height)
                )
            }
        }

        // 3. Frosted glass content card
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier
                .padding(16.dp)
                .fillMaxWidth(0.9f)
                .clip(RoundedCornerShape(24.dp))
                .background(Color(0x14FFFFFF)) // Semi-translucent white
                .padding(horizontal = 16.dp, vertical = 24.dp)
        ) {
            Text(
                text = phase.uppercase(),
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFFFB7185),
                letterSpacing = 2.sp,
                fontFamily = FontFamily.SansSerif
            )
            
            Spacer(modifier = Modifier.height(10.dp))

            // Celebrating mascot companion to mark the completion win
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(16.dp),
                modifier = Modifier
                    .padding(horizontal = 8.dp)
                    .fillMaxWidth()
            ) {
                ProceduralMascot(
                    type = mascotType,
                    expression = MascotExpression.CELEBRATING,
                    onClick = {},
                    modifier = Modifier.size(75.dp)
                )
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Session Completed! 🎉",
                        color = Color.White,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "You earned +20 XP! Great job focusing. Let's recharge!",
                        color = Color(0xB3FFFFFF),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Normal
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Display break GIF
            if (selectedGifPath != null) {
                GifImage(
                    gifUri = selectedGifPath,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(240.dp)
                        .clip(RoundedCornerShape(12.dp))
                )
                Spacer(modifier = Modifier.height(16.dp))
            } else {
                Text(
                    text = "Time to step away and rest.",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color(0xB3FFFFFF),
                    fontFamily = FontFamily.SansSerif
                )
                Spacer(modifier = Modifier.height(16.dp))
            }

            // Large digital timer
            Text(
                text = timeString,
                fontSize = 64.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White,
                fontFamily = FontFamily.Monospace
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Control Buttons Row
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth()
            ) {
                // Mute/Unmute Button (Unicode design)
                Button(
                    onClick = { isMuted = !isMuted },
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Color(0x1EFFFFFF),
                        contentColor = Color.White
                    ),
                    contentPadding = PaddingValues(horizontal = 4.dp, vertical = 8.dp),
                    modifier = Modifier.weight(1f)
                ) {
                    Text(
                        text = if (isMuted) "🔊 Play" else "🔇 Mute",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1
                    )
                }

                // Skip Button
                Button(
                    onClick = {
                        TimerService.skip(context)
                    },
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Color(0x1EFFFFFF), // Frosted ghost
                        contentColor = Color.White
                    ),
                    contentPadding = PaddingValues(horizontal = 4.dp, vertical = 8.dp),
                    modifier = Modifier.weight(1f)
                ) {
                    Text(
                        text = "Skip",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1
                    )
                }

                // Close UI button
                Button(
                    onClick = {
                        onDismiss()
                    },
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Color(0xFFFB7185),
                        contentColor = Color.White
                    ),
                    contentPadding = PaddingValues(horizontal = 4.dp, vertical = 8.dp),
                    modifier = Modifier.weight(1f)
                ) {
                    Text(
                        text = "Close",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1
                    )
                }
            }
        }
    }
}

@Composable
fun GifImage(
    gifUri: String,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    AndroidView(
        factory = { ctx ->
            ImageView(ctx).apply {
                scaleType = ImageView.ScaleType.FIT_CENTER
            }
        },
        update = { imageView ->
            try {
                if (gifUri.startsWith("gifs/")) {
                    // Load from assets folder
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                        val source = ImageDecoder.createSource(context.assets, gifUri)
                        val drawable = ImageDecoder.decodeDrawable(source)
                        imageView.setImageDrawable(drawable)
                        if (drawable is AnimatedImageDrawable) {
                            drawable.start()
                        }
                    } else {
                        // Fallback
                        val stream = context.assets.open(gifUri)
                        val bitmap = android.graphics.BitmapFactory.decodeStream(stream)
                        imageView.setImageBitmap(bitmap)
                    }
                } else {
                    // Load local URI
                    val uri = Uri.parse(gifUri)
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                        val source = ImageDecoder.createSource(context.contentResolver, uri)
                        val drawable = ImageDecoder.decodeDrawable(source)
                        imageView.setImageDrawable(drawable)
                        if (drawable is AnimatedImageDrawable) {
                            drawable.start()
                        }
                    } else {
                        imageView.setImageURI(uri)
                    }
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        },
        modifier = modifier
    )
}

private data class ParticleData(
    val x: Float,
    val y: Float,
    val size: Float,
    val speed: Float
)

private fun getGifPaths(context: android.content.Context, path: String): List<String> {
    val gifs = mutableListOf<String>()
    try {
        val list = context.assets.list(path) ?: return emptyList()
        for (item in list) {
            val childPath = if (path.isEmpty()) item else "$path/$item"
            if (item.endsWith(".gif", ignoreCase = true)) {
                gifs.add(childPath)
            } else {
                gifs.addAll(getGifPaths(context, childPath))
            }
        }
    } catch (e: Exception) {
        e.printStackTrace()
    }
    return gifs
}

private fun getSoundPaths(context: android.content.Context, path: String): List<String> {
    val sounds = mutableListOf<String>()
    try {
        val list = context.assets.list(path) ?: return emptyList()
        for (item in list) {
            val childPath = if (path.isEmpty()) item else "$path/$item"
            if (item.endsWith(".mp3", ignoreCase = true) || 
                item.endsWith(".wav", ignoreCase = true) || 
                item.endsWith(".ogg", ignoreCase = true)) {
                sounds.add(childPath)
            } else {
                sounds.addAll(getSoundPaths(context, childPath))
            }
        }
    } catch (e: Exception) {
        e.printStackTrace()
    }
    return sounds
}
