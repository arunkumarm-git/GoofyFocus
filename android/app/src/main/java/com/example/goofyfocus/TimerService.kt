package com.example.goofyfocus

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

class TimerService : Service() {

    private val serviceJob = Job()
    private val serviceScope = CoroutineScope(Dispatchers.Main + serviceJob)
    private var timerJob: Job? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        loadPreferences()
    }

    private fun loadPreferences() {
        val prefs = getSharedPreferences("GoofyFocusPrefs", Context.MODE_PRIVATE)
        isPro.value = prefs.getBoolean("IS_PRO", false)
        customGifUri.value = prefs.getString("CUSTOM_GIF_URI", null)
        mascotType.value = prefs.getString("MASCOT_TYPE", "cat") ?: "cat"
        
        // Load custom settings
        workSecs.value = prefs.getInt("WORK_SECS", 25 * 60)
        shortBreakSecs.value = prefs.getInt("SHORT_BREAK_SECS", 5 * 60)
        longBreakSecs.value = prefs.getInt("LONG_BREAK_SECS", 15 * 60)
        sessionsPerCycle.value = prefs.getInt("SESSIONS_PER_CYCLE", 4)
        breakFlow.value = prefs.getString("BREAK_FLOW", "auto") ?: "auto"
        
        if (!isRunning.value) {
            remainingSecs.value = when (currentPhase.value) {
                "Work" -> workSecs.value
                "Short Break" -> shortBreakSecs.value
                "Long Break" -> longBreakSecs.value
                else -> workSecs.value
            }
            totalSecs.value = remainingSecs.value
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> startTimer()
            ACTION_PAUSE -> pauseTimer()
            ACTION_SKIP -> skipTimer()
            ACTION_RESET -> resetTimer()
            ACTION_UPDATE_SETTINGS -> {
                // Settings updated via static flows
            }
        }
        
        // Start foreground service with initial notification
        startForeground(NOTIFICATION_ID, buildNotification())
        
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun startTimer() {
        if (isRunning.value) return
        isRunning.value = true
        timerJob = serviceScope.launch {
            while (isRunning.value && remainingSecs.value > 0) {
                delay(1000)
                remainingSecs.value -= 1
                updateNotification()
            }
            if (remainingSecs.value <= 0) {
                handlePhaseCompletion()
            }
        }
        updateNotification()
    }

    private fun pauseTimer() {
        isRunning.value = false
        timerJob?.cancel()
        timerJob = null
        updateNotification()
    }

    private fun skipTimer() {
        val wasRunning = isRunning.value
        pauseTimer()
        
        if (currentPhase.value == "Work") {
            sessionsCompleted.value += 1
            currentPhase.value = decideBreak()
            remainingSecs.value = getDurationForPhase(currentPhase.value)
            totalSecs.value = remainingSecs.value
            
            // Launch Break Overlay Screen/Activity
            launchBreakActivity()
        } else {
            currentPhase.value = "Work"
            remainingSecs.value = workSecs.value
            totalSecs.value = remainingSecs.value
        }
        
        if (wasRunning) {
            startTimer()
        } else {
            updateNotification()
        }
    }

    private fun resetTimer() {
        pauseTimer()
        sessionsCompleted.value = 0
        currentPhase.value = "Work"
        remainingSecs.value = workSecs.value
        totalSecs.value = remainingSecs.value
        updateNotification()
    }

    private fun handlePhaseCompletion() {
        // Ticks down to 0, automatically moves to the next phase
        skipTimer()
    }

    private fun decideBreak(): String {
        return when (breakFlow.value) {
            "always_short" -> "Short Break"
            "always_long" -> "Long Break"
            else -> {
                if (sessionsCompleted.value % sessionsPerCycle.value == 0) "Long Break"
                else "Short Break"
            }
        }
    }

    private fun getDurationForPhase(phase: String): Int {
        return when (phase) {
            "Work" -> workSecs.value
            "Short Break" -> shortBreakSecs.value
            "Long Break" -> longBreakSecs.value
            else -> workSecs.value
        }
    }

    private fun launchBreakActivity() {
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
            putExtra("LAUNCH_BREAK_OVERLAY", true)
        }
        
        // Build ActivityOptions to allow background activity starts on Android 14+
        val options = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            android.app.ActivityOptions.makeBasic().apply {
                setPendingIntentBackgroundActivityStartMode(
                    android.app.ActivityOptions.MODE_BACKGROUND_ACTIVITY_START_ALLOWED
                )
            }
        } else {
            null
        }

        val flags = PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        val pendingIntent = PendingIntent.getActivity(
            this, 
            1002, 
            intent, 
            flags
        )
        
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("GoofyFocus: Break Time! ☕")
            .setContentText("Tap to open break overlay.")
            .setSmallIcon(android.R.drawable.ic_media_play)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setFullScreenIntent(pendingIntent, true)
            .setAutoCancel(true)
            .build()
            
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(NOTIFICATION_ID, notification)
        
        try {
            if (options != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                pendingIntent.send(this, 0, null, null, null, null, options.toBundle())
            } else {
                startActivity(intent)
            }
        } catch (e: Exception) {
            try {
                startActivity(intent)
            } catch (ex: Exception) {
                ex.printStackTrace()
            }
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "GoofyFocus Timer",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Shows the active countdown timer"
            }
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification {
        val minutes = remainingSecs.value / 60
        val seconds = remainingSecs.value % 60
        val timeString = String.format("%02d:%02d", minutes, seconds)
        val contentTitle = "${currentPhase.value} Session"
        val contentText = "$timeString remaining"

        val openAppIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        val flags = PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        val openAppPendingIntent = PendingIntent.getActivity(this, 0, openAppIntent, flags)

        // Actions
        val playPauseAction = if (isRunning.value) {
            val intent = Intent(this, TimerService::class.java).apply { action = ACTION_PAUSE }
            val pending = PendingIntent.getService(this, 1, intent, flags)
            NotificationCompat.Action.Builder(android.R.drawable.ic_media_pause, "Pause", pending).build()
        } else {
            val intent = Intent(this, TimerService::class.java).apply { action = ACTION_START }
            val pending = PendingIntent.getService(this, 2, intent, flags)
            NotificationCompat.Action.Builder(android.R.drawable.ic_media_play, "Resume", pending).build()
        }

        val skipIntent = Intent(this, TimerService::class.java).apply { action = ACTION_SKIP }
        val skipPending = PendingIntent.getService(this, 3, skipIntent, flags)
        val skipAction = NotificationCompat.Action.Builder(android.R.drawable.ic_media_next, "Skip", skipPending).build()

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(contentTitle)
            .setContentText(contentText)
            .setSmallIcon(android.R.drawable.ic_media_play)
            .setContentIntent(openAppPendingIntent)
            .addAction(playPauseAction)
            .addAction(skipAction)
            .setOngoing(true)
            .build()
    }

    private fun updateNotification() {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(NOTIFICATION_ID, buildNotification())
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceJob.cancel()
    }

    companion object {
        const val CHANNEL_ID = "goofy_focus_timer_channel"
        const val NOTIFICATION_ID = 1001

        const val ACTION_START = "ACTION_START"
        const val ACTION_PAUSE = "ACTION_PAUSE"
        const val ACTION_SKIP = "ACTION_SKIP"
        const val ACTION_RESET = "ACTION_RESET"
        const val ACTION_UPDATE_SETTINGS = "ACTION_UPDATE_SETTINGS"

        val remainingSecs = MutableStateFlow(25 * 60)
        val totalSecs = MutableStateFlow(25 * 60)
        val currentPhase = MutableStateFlow("Work")
        val isRunning = MutableStateFlow(false)
        val sessionsCompleted = MutableStateFlow(0)

        // Settings (in seconds)
        val workSecs = MutableStateFlow(25 * 60)
        val shortBreakSecs = MutableStateFlow(5 * 60)
        val longBreakSecs = MutableStateFlow(15 * 60)
        val sessionsPerCycle = MutableStateFlow(4)
        val breakFlow = MutableStateFlow("auto")

        // Premium State Flows
        val isPro = MutableStateFlow(false)
        val customGifUri = MutableStateFlow<String?>(null)
        val mascotType = MutableStateFlow("cat") // cat, dog

        fun start(context: Context) {
            val intent = Intent(context, TimerService::class.java).apply { action = ACTION_START }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun pause(context: Context) {
            val intent = Intent(context, TimerService::class.java).apply { action = ACTION_PAUSE }
            context.startService(intent)
        }

        fun skip(context: Context) {
            val intent = Intent(context, TimerService::class.java).apply { action = ACTION_SKIP }
            context.startService(intent)
        }

        fun reset(context: Context) {
            val intent = Intent(context, TimerService::class.java).apply { action = ACTION_RESET }
            context.startService(intent)
        }

        fun updateSettings(context: Context, workMins: Int, shortMins: Int, longMins: Int, flow: String) {
            workSecs.value = workMins * 60
            shortBreakSecs.value = shortMins * 60
            longBreakSecs.value = longMins * 60
            breakFlow.value = flow
            
            // Save settings locally
            val prefs = context.getSharedPreferences("GoofyFocusPrefs", Context.MODE_PRIVATE)
            prefs.edit().apply {
                putInt("WORK_SECS", workSecs.value)
                putInt("SHORT_BREAK_SECS", shortBreakSecs.value)
                putInt("LONG_BREAK_SECS", longBreakSecs.value)
                putString("BREAK_FLOW", breakFlow.value)
                apply()
            }
            
            if (!isRunning.value) {
                remainingSecs.value = when (currentPhase.value) {
                    "Work" -> workSecs.value
                    "Short Break" -> shortBreakSecs.value
                    "Long Break" -> longBreakSecs.value
                    else -> workSecs.value
                }
                totalSecs.value = remainingSecs.value
            }

            val intent = Intent(context, TimerService::class.java).apply { action = ACTION_UPDATE_SETTINGS }
            context.startService(intent)
        }

        fun setProEnabled(context: Context, enabled: Boolean) {
            isPro.value = enabled
            val prefs = context.getSharedPreferences("GoofyFocusPrefs", Context.MODE_PRIVATE)
            prefs.edit().putBoolean("IS_PRO", enabled).apply()
        }

        fun saveCustomGifUri(context: Context, uri: String?) {
            customGifUri.value = uri
            val prefs = context.getSharedPreferences("GoofyFocusPrefs", Context.MODE_PRIVATE)
            prefs.edit().putString("CUSTOM_GIF_URI", uri).apply()
        }

        fun setMascotType(context: Context, type: String) {
            mascotType.value = type
            val prefs = context.getSharedPreferences("GoofyFocusPrefs", Context.MODE_PRIVATE)
            prefs.edit().putString("MASCOT_TYPE", type).apply()
        }
    }
}
