package com.arunkumar.goofyfocus.ui.main

import android.content.Context
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.border
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
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
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation3.runtime.NavKey
import kotlinx.coroutines.launch
import com.arunkumar.goofyfocus.MainActivity
import com.arunkumar.goofyfocus.Settings
import com.arunkumar.goofyfocus.TimerService
import com.arunkumar.goofyfocus.ui.MascotWithBubble
import com.arunkumar.goofyfocus.ui.ProceduralMascot
import com.arunkumar.goofyfocus.ui.MascotExpression
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

    // Progression XP levels
    val focusXp by TimerService.focusXp.collectAsStateWithLifecycle()
    val focusLevel by TimerService.focusLevel.collectAsStateWithLifecycle()
    val mascotType by TimerService.mascotType.collectAsStateWithLifecycle()
    val isPro by TimerService.isPro.collectAsStateWithLifecycle()
    val proExpiryTime by TimerService.proExpiryTime.collectAsStateWithLifecycle()

    var selectedTab by remember { mutableIntStateOf(0) }
    val coroutineScope = rememberCoroutineScope()
    val pagerState = rememberPagerState(pageCount = { 3 })
    var showLevelUpDialog by remember { mutableStateOf(false) }
    var levelUpTo by remember { mutableIntStateOf(1) }

    // Focus Sounds states
    var activeSound by remember { mutableStateOf<String?>(null) }
    var showAdPassDialog by remember { mutableStateOf(false) }
    var soundToPlayOnReward by remember { mutableStateOf<String?>(null) }

    // Sync active sound on launch
    LaunchedEffect(Unit) {
        if (com.arunkumar.goofyfocus.audio.SoundSynthesizer.isPlaying()) {
            activeSound = com.arunkumar.goofyfocus.audio.SoundSynthesizer.getPlayingType()
        }
    }

    // Local Todo checklist states
    val todoItems = remember { mutableStateListOf<TodoItem>() }
    val prefs = remember { context.getSharedPreferences("GoofyFocusPrefs", Context.MODE_PRIVATE) }
    LaunchedEffect(Unit) {
        val savedStr = prefs.getString("TODO_LIST_ITEMS", "") ?: ""
        if (savedStr.isNotEmpty()) {
            val loaded = savedStr.split(";;;").mapNotNull {
                val parts = it.split("|||")
                if (parts.size == 3) {
                    TodoItem(parts[0], parts[1], parts[2].toBoolean())
                } else null
            }
            todoItems.clear()
            todoItems.addAll(loaded)
        }
    }
    val saveTasks = { itemsList: List<TodoItem> ->
        val savedStr = itemsList.joinToString(";;;") { "${it.id}|||${it.title}|||${it.isCompleted}" }
        prefs.edit().putString("TODO_LIST_ITEMS", savedStr).apply()
    }

    LaunchedEffect(Unit) {
        TimerService.levelUpEvent.collect { level ->
            levelUpTo = level
            showLevelUpDialog = true
        }
    }

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
                    IconButton(onClick = {
                        com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                        onItemClick(Settings)
                    }) {
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
        bottomBar = {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color(0xFF0F0D0E))
                    .padding(bottom = 16.dp, start = 24.dp, end = 24.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(60.dp)
                        .clip(RoundedCornerShape(30.dp))
                        .background(Color(0xFF171415))
                        .border(1.dp, Color(0x1AFFFFFF), RoundedCornerShape(30.dp)),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceAround
                ) {
                    val tabs = listOf(
                        Triple(0, "Timer", "⏱️"),
                        Triple(1, "Tasks", "📝"),
                        Triple(2, "Sounds", "🎵")
                    )
                    
                    tabs.forEach { (index, label, emoji) ->
                        val isSelected = selectedTab == index
                        val activeBg = if (isSelected) Color(0x26FB7185) else Color.Transparent
                        val activeBorderColor = if (isSelected) Color(0xFFFB7185) else Color.Transparent
                        val contentColor = if (isSelected) Color.White else Color(0x80FFFFFF)
                        
                        Box(
                            contentAlignment = Alignment.Center,
                            modifier = Modifier
                                .weight(1f)
                                .fillMaxHeight()
                                .clickable {
                                    com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                    selectedTab = index
                                    coroutineScope.launch {
                                        pagerState.animateScrollToPage(index)
                                    }
                                }
                        ) {
                            Row(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(20.dp))
                                    .background(activeBg)
                                    .border(if (isSelected) 1.dp else 0.dp, activeBorderColor, RoundedCornerShape(20.dp))
                                    .padding(horizontal = 12.dp, vertical = 8.dp),
                                horizontalArrangement = Arrangement.spacedBy(6.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(emoji, fontSize = 16.sp)
                                if (isSelected) {
                                    Text(
                                        text = label,
                                        color = contentColor,
                                        fontSize = 12.sp,
                                        fontWeight = FontWeight.Bold
                                    )
                                }
                            }
                        }
                    }
                }
            }
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

            // Foreground Layout switching by selected tab index

            LaunchedEffect(selectedTab) {
                if (pagerState.currentPage != selectedTab) {
                    pagerState.animateScrollToPage(selectedTab)
                }
            }
            
            LaunchedEffect(pagerState.currentPage) {
                selectedTab = pagerState.currentPage
            }

            HorizontalPager(
                state = pagerState,
                modifier = Modifier.fillMaxSize()
            ) { page ->
                when (page) {
                0 -> {
                    // Timer Tab (Non-scrollable, perfectly centered)
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.SpaceBetween
                    ) {
                        // Phase Indicator Card
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
                            Canvas(modifier = Modifier.fillMaxSize()) {
                                val strokeWidthPx = 10.dp.toPx()
                                val diameter = size.minDimension - strokeWidthPx
                                val topLeft = Offset(strokeWidthPx / 2, strokeWidthPx / 2)
                                
                                drawCircle(
                                    color = Color(0x1AFFFFFF),
                                    radius = diameter / 2,
                                    center = center,
                                    style = Stroke(width = strokeWidthPx)
                                )

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

                        // 2. Completed Sessions tracker
                        SessionProgressTracker(
                            completed = completedSessions % sessionsPerCycle,
                            total = sessionsPerCycle,
                            accentColor = accentPink
                        )

                        // 3. Mascot Companion & Progression Tracker
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            MascotWithBubble(
                                isRunning = isRunning,
                                currentPhase = phase,
                                modifier = Modifier.height(170.dp)
                            )
                            
                            val levelTitle = when (focusLevel) {
                                1 -> "Focus Seedling 🌱"
                                2 -> "Curious Learner 🎓"
                                3 -> "Habit Builder 🔨"
                                4 -> "Mindfulness Practitioner 🧘"
                                5 -> "Zen Master 🕉️"
                                6 -> "Focus Wizard 🧙"
                                else -> "Legendary Companion 👑"
                            }
                            val xpInCurrentLevel = focusXp - (focusLevel - 1) * 100
                            val xpProgress = xpInCurrentLevel / 100f
                            val animatedXpProgress by animateFloatAsState(
                                targetValue = xpProgress,
                                animationSpec = tween(1000, easing = EaseInOutCubic),
                                label = "xp_progress"
                            )

                            Column(
                                horizontalAlignment = Alignment.CenterHorizontally,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(horizontal = 24.dp)
                            ) {
                                Row(
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Text(
                                        text = "Level $focusLevel: $levelTitle",
                                        color = Color(0xFFFCD34D),
                                        fontSize = 12.sp,
                                        fontWeight = FontWeight.Bold
                                    )
                                    Text(
                                        text = "$xpInCurrentLevel / 100 XP",
                                        color = Color(0x80FFFFFF),
                                        fontSize = 11.sp,
                                        fontWeight = FontWeight.Medium
                                    )
                                }
                                Spacer(modifier = Modifier.height(6.dp))
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(8.dp)
                                        .clip(RoundedCornerShape(4.dp))
                                        .background(Color(0x1AFFFFFF))
                                ) {
                                    Box(
                                        modifier = Modifier
                                            .fillMaxHeight()
                                            .fillMaxWidth(animatedXpProgress)
                                            .background(
                                                Brush.horizontalGradient(
                                                    colors = listOf(accentPink, accentPurple)
                                                )
                                            )
                                    )
                                }
                            }
                        }

                        // 4. Control Row (Fixed bottom content)
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(24.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.padding(bottom = 16.dp)
                        ) {
                            IconButton(
                                onClick = {
                                    com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                    TimerService.reset(context)
                                },
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

                            Button(
                                onClick = {
                                    com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
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

                            IconButton(
                                onClick = {
                                    com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                    TimerService.skip(context)
                                },
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
                
                1 -> {
                    // Tasks Tab (Dedicated Full-Page Scrollable Layout)
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .verticalScroll(rememberScrollState())
                            .padding(24.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "My Focus Goals 📝",
                            color = Color.White,
                            fontSize = 22.sp,
                            fontWeight = FontWeight.Bold
                        )
                        
                        // Tasks Progress Card
                        val totalTasks = todoItems.size
                        val completedTasks = todoItems.count { it.isCompleted }
                        val tasksProgress = if (totalTasks > 0) completedTasks.toFloat() / totalTasks.toFloat() else 0f
                        
                        Card(
                            colors = CardDefaults.cardColors(containerColor = Color(0x0CFFFFFF)),
                            shape = RoundedCornerShape(16.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(
                                modifier = Modifier.padding(16.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                Row(
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Text("Daily Progress", color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                                    Text("$completedTasks of $totalTasks finished", color = accentPink, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                                }
                                
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(8.dp)
                                        .clip(RoundedCornerShape(4.dp))
                                        .background(Color(0x1AFFFFFF))
                                ) {
                                    Box(
                                        modifier = Modifier
                                            .fillMaxHeight()
                                            .fillMaxWidth(tasksProgress)
                                            .background(accentPink)
                                    )
                                }
                            }
                        }
                        
                        // Add Task Input Row
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            var newTaskTitle by remember { mutableStateOf("") }
                            
                            TextField(
                                value = newTaskTitle,
                                onValueChange = { newTaskTitle = it },
                                placeholder = { Text("Add focus task...", color = Color(0x66FFFFFF), fontSize = 13.sp) },
                                modifier = Modifier.weight(1f),
                                singleLine = true,
                                colors = TextFieldDefaults.colors(
                                    focusedContainerColor = Color(0x0DFFFFFF),
                                    unfocusedContainerColor = Color(0x0DFFFFFF),
                                    focusedTextColor = Color.White,
                                    unfocusedTextColor = Color.White,
                                    focusedIndicatorColor = accentPink,
                                    unfocusedIndicatorColor = Color.Transparent
                                )
                            )
                            Button(
                                onClick = {
                                    com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                    if (newTaskTitle.trim().isNotEmpty()) {
                                        val newItem = TodoItem(
                                            id = java.util.UUID.randomUUID().toString(),
                                            title = newTaskTitle.trim(),
                                            isCompleted = false
                                        )
                                        todoItems.add(newItem)
                                        saveTasks(todoItems)
                                        newTaskTitle = ""
                                    }
                                },
                                colors = ButtonDefaults.buttonColors(containerColor = accentPink),
                                shape = RoundedCornerShape(8.dp)
                            ) {
                                Text("Add", fontWeight = FontWeight.Bold, fontSize = 13.sp)
                            }
                        }
                        
                        // Tasks List
                        if (todoItems.isEmpty()) {
                            Text(
                                text = "No tasks yet. Stay productive! 🚀",
                                color = Color(0x80FFFFFF),
                                fontSize = 14.sp,
                                textAlign = TextAlign.Center,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 40.dp)
                            )
                        } else {
                            Column(
                                verticalArrangement = Arrangement.spacedBy(8.dp),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                todoItems.forEach { item ->
                                    Row(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .background(Color(0x0CFFFFFF), RoundedCornerShape(12.dp))
                                            .padding(horizontal = 12.dp, vertical = 6.dp),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Row(
                                            verticalAlignment = Alignment.CenterVertically,
                                            modifier = Modifier.weight(1f)
                                        ) {
                                            Checkbox(
                                                checked = item.isCompleted,
                                                onCheckedChange = { isChecked ->
                                                    com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                                    if (isChecked) {
                                                        com.arunkumar.goofyfocus.audio.SoundSynthesizer.playSuccessSound()
                                                    }
                                                    val index = todoItems.indexOfFirst { it.id == item.id }
                                                    if (index != -1) {
                                                        todoItems[index] = item.copy(isCompleted = isChecked)
                                                        saveTasks(todoItems)
                                                    }
                                                },
                                                colors = CheckboxDefaults.colors(
                                                    checkedColor = accentPink,
                                                    uncheckedColor = Color(0x66FFFFFF)
                                                )
                                            )
                                            Text(
                                                text = item.title,
                                                color = if (item.isCompleted) Color(0x80FFFFFF) else Color.White,
                                                fontSize = 14.sp,
                                                style = if (item.isCompleted) LocalTextStyle.current.copy(
                                                    textDecoration = androidx.compose.ui.text.style.TextDecoration.LineThrough
                                                ) else LocalTextStyle.current
                                            )
                                        }
                                        IconButton(
                                            onClick = {
                                                com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                                todoItems.removeIf { it.id == item.id }
                                                saveTasks(todoItems)
                                            }
                                        ) {
                                            Icon(
                                                painter = painterResource(android.R.drawable.ic_menu_delete),
                                                contentDescription = "Delete",
                                                tint = Color(0xFFEF4444),
                                                modifier = Modifier.size(22.dp)
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                
                2 -> {
                    // Sounds Tab (Dedicated Full-Page Scrollable Layout)
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .verticalScroll(rememberScrollState())
                            .padding(24.dp),
                        verticalArrangement = Arrangement.spacedBy(20.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "Focus Soundscapes 🎵",
                            color = Color.White,
                            fontSize = 22.sp,
                            fontWeight = FontWeight.Bold
                        )
                        
                        Text(
                            text = "Select a synthesized background wave to block distractions and entrain peak focus.",
                            color = Color(0xB3FFFFFF),
                            fontSize = 13.sp,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.fillMaxWidth()
                        )
                        
                        // Procedural animated visualizer bar row when playing
                        if (activeSound != null) {
                            Row(
                                horizontalArrangement = Arrangement.spacedBy(4.dp),
                                verticalAlignment = Alignment.Bottom,
                                modifier = Modifier
                                    .height(48.dp)
                                    .padding(vertical = 8.dp)
                            ) {
                                val transition = rememberInfiniteTransition(label = "equalizer")
                                for (i in 0 until 4) {
                                    val duration = 800 + i * 200
                                    val heightPercent by transition.animateFloat(
                                        initialValue = 0.2f,
                                        targetValue = 1.0f,
                                        animationSpec = infiniteRepeatable(
                                            animation = tween(duration, easing = LinearEasing),
                                            repeatMode = RepeatMode.Reverse
                                        ),
                                        label = "eq_bar"
                                    )
                                    Box(
                                        modifier = Modifier
                                            .width(6.dp)
                                            .fillMaxHeight(heightPercent)
                                            .clip(RoundedCornerShape(3.dp))
                                            .background(accentPink)
                                    )
                                }
                            }
                        } else {
                            Text("🔇 Silent", color = Color(0x66FFFFFF), fontSize = 14.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(vertical = 12.dp))
                        }
                        
                        Card(
                            colors = CardDefaults.cardColors(containerColor = Color(0x0CFFFFFF)),
                            shape = RoundedCornerShape(16.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(
                                modifier = Modifier.padding(16.dp),
                                verticalArrangement = Arrangement.spacedBy(16.dp),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                                    Row(
                                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        SoundChip(
                                            label = "White Noise 💨",
                                            active = activeSound == "white",
                                            modifier = Modifier.weight(1f),
                                            onClick = {
                                                com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                                if (isPro) {
                                                    activeSound = "white"
                                                    com.arunkumar.goofyfocus.audio.SoundSynthesizer.play("white")
                                                } else {
                                                    soundToPlayOnReward = "white"
                                                    showAdPassDialog = true
                                                }
                                            }
                                        )
                                        SoundChip(
                                            label = "Brown Noise 🌊",
                                            active = activeSound == "brown",
                                            modifier = Modifier.weight(1f),
                                            onClick = {
                                                com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                                if (isPro) {
                                                    activeSound = "brown"
                                                    com.arunkumar.goofyfocus.audio.SoundSynthesizer.play("brown")
                                                } else {
                                                    soundToPlayOnReward = "brown"
                                                    showAdPassDialog = true
                                                }
                                            }
                                        )
                                    }
                                    Row(
                                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        SoundChip(
                                            label = "Alpha Focus 🧠",
                                            active = activeSound == "alpha",
                                            modifier = Modifier.weight(1f),
                                            onClick = {
                                                com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                                if (isPro) {
                                                    activeSound = "alpha"
                                                    com.arunkumar.goofyfocus.audio.SoundSynthesizer.play("alpha")
                                                } else {
                                                    soundToPlayOnReward = "alpha"
                                                    showAdPassDialog = true
                                                }
                                            }
                                        )
                                        SoundChip(
                                            label = "Theta Deep 🧘",
                                            active = activeSound == "theta",
                                            modifier = Modifier.weight(1f),
                                            onClick = {
                                                com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                                if (isPro) {
                                                    activeSound = "theta"
                                                    com.arunkumar.goofyfocus.audio.SoundSynthesizer.play("theta")
                                                } else {
                                                    soundToPlayOnReward = "theta"
                                                    showAdPassDialog = true
                                                }
                                            }
                                        )
                                    }
                                }
                                
                                if (activeSound != null) {
                                    Button(
                                        onClick = {
                                            com.arunkumar.goofyfocus.audio.SoundSynthesizer.playClickSound()
                                            activeSound = null
                                            com.arunkumar.goofyfocus.audio.SoundSynthesizer.stop()
                                        },
                                        colors = ButtonDefaults.buttonColors(containerColor = Color(0x1EFB7185), contentColor = accentPink),
                                        shape = RoundedCornerShape(12.dp),
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        Text("Stop Playback ⏹️", fontWeight = FontWeight.Bold)
                                    }
                                }
                            }
                        }
                        
                        Card(
                            colors = CardDefaults.cardColors(containerColor = Color(0x06FFFFFF)),
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(
                                modifier = Modifier.padding(12.dp),
                                verticalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                Text("🎓 What are Binaural Beats?", color = Color(0xFFFCD34D), fontSize = 13.sp, fontWeight = FontWeight.Bold)
                                Text("Binaural beats play slightly different audio frequencies in the left and right ears. The brain synthesizes the difference (e.g. 200Hz vs 210Hz creates a 10Hz Alpha beat), encouraging brainwaves to enter focus or deep relaxation states.", color = Color(0x80FFFFFF), fontSize = 11.sp)
                            }
                        }
                    }
                }
            }
            }

            // Overlay Dialogs displayed over any active tab
            if (showLevelUpDialog) {
                AlertDialog(
                    onDismissRequest = { showLevelUpDialog = false },
                    title = {
                        Text(
                            text = "🎉 LEVEL UP! 🎉",
                            fontWeight = FontWeight.ExtraBold,
                            fontSize = 22.sp,
                            color = Color(0xFFFCD34D),
                            textAlign = TextAlign.Center,
                            modifier = Modifier.fillMaxWidth()
                        )
                    },
                    text = {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            ProceduralMascot(
                                type = mascotType,
                                expression = MascotExpression.CELEBRATING,
                                onClick = {},
                                modifier = Modifier.size(120.dp)
                            )
                            Spacer(modifier = Modifier.height(16.dp))
                            Text(
                                text = "Your companion reached Level $levelUpTo!",
                                color = Color.White,
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                textAlign = TextAlign.Center
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(
                                text = "You are building strong habits and learning to focus! Keep going to grow your companion even more. 🌱",
                                color = Color(0xB3FFFFFF),
                                fontSize = 13.sp,
                                textAlign = TextAlign.Center
                            )
                        }
                    },
                    confirmButton = {
                        Button(
                            onClick = { showLevelUpDialog = false },
                            colors = ButtonDefaults.buttonColors(
                                containerColor = accentPink,
                                contentColor = Color.White
                            ),
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Awesome!", fontWeight = FontWeight.Bold)
                        }
                    },
                    containerColor = Color(0xFF171415),
                    titleContentColor = Color.White,
                    textContentColor = Color(0xB3FFFFFF)
                )
            }

            if (showAdPassDialog) {
                val isAdReady by MainActivity.isAdLoaded.collectAsStateWithLifecycle()
                
                AlertDialog(
                    onDismissRequest = { showAdPassDialog = false },
                    title = {
                        Text(
                            text = "✨ One Day Sound Pass 🎟️",
                            fontWeight = FontWeight.ExtraBold,
                            fontSize = 18.sp,
                            color = Color(0xFFA78BFA),
                            textAlign = TextAlign.Center,
                            modifier = Modifier.fillMaxWidth()
                        )
                    },
                    text = {
                        Text(
                            text = "Watch a rewarded ad to unlock all focus sounds & premium features free for 24 hours!",
                            color = Color.White,
                            fontSize = 13.sp,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.fillMaxWidth()
                        )
                    },
                    confirmButton = {
                        Button(
                            onClick = {
                                val activity = context as? android.app.Activity
                                if (activity != null && isAdReady) {
                                    MainActivity.showRewardedAd(
                                        activity,
                                        onRewardEarned = {
                                            TimerService.grant24HourPass(context)
                                            showAdPassDialog = false
                                            soundToPlayOnReward?.let {
                                                activeSound = it
                                                com.arunkumar.goofyfocus.audio.SoundSynthesizer.play(it)
                                            }
                                            android.widget.Toast.makeText(context, "Premium Pass activated! 🎉", android.widget.Toast.LENGTH_SHORT).show()
                                        },
                                        onAdClosedOrFailed = {
                                            android.widget.Toast.makeText(context, "Failed to load ad. Please try again.", android.widget.Toast.LENGTH_SHORT).show()
                                        }
                                    )
                                } else {
                                    android.widget.Toast.makeText(context, "Ad is loading, please try again in a few seconds.", android.widget.Toast.LENGTH_SHORT).show()
                                }
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFA78BFA)),
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                text = if (isAdReady) "Claim Sound Pass 🎟️" else "Ad Loading... ⏳",
                                fontWeight = FontWeight.Bold
                            )
                        }
                    },
                    dismissButton = {
                        TextButton(
                            onClick = { showAdPassDialog = false },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Not Now", color = Color(0x80FFFFFF))
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

@Composable
fun SoundChip(
    label: String,
    active: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    val bgColor = if (active) Color(0xFFFB7185) else Color(0x14FFFFFF)
    val contentColor = if (active) Color.White else Color(0xB3FFFFFF)
    
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .clip(RoundedCornerShape(10.dp))
            .background(bgColor)
            .clickable { onClick() }
            .padding(vertical = 10.dp, horizontal = 12.dp)
    ) {
        Text(
            text = label,
            color = contentColor,
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center
        )
    }
}

data class TodoItem(
    val id: String,
    val title: String,
    val isCompleted: Boolean
)
