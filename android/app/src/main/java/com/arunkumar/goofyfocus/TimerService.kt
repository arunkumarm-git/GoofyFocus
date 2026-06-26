package com.arunkumar.goofyfocus

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
    private var hourlyDecrementJob: Job? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        loadPreferences()
        startHourlyDecrementTask()
    }


    private fun startHourlyDecrementTask() {
        hourlyDecrementJob?.cancel()
        hourlyDecrementJob = serviceScope.launch {
            while (true) {
                delay(60000)
                if (isPro.value && premiumHours.value > 0) {
                    val syncTime = lastPremiumSyncAt.value
                    if (syncTime > 0L) {
                        val elapsedMillis = System.currentTimeMillis() - syncTime
                        val elapsedHours = (elapsedMillis / (3600 * 1000L)).toInt()
                        if (elapsedHours > 0) {
                            val currentHours = premiumHours.value
                            val newHours = Math.max(0, currentHours - elapsedHours)
                            premiumHours.value = newHours
                            lastPremiumSyncAt.value = syncTime + elapsedHours * 3600 * 1000L
                            
                            val prefs = getSharedPreferences("GoofyFocusPrefs", Context.MODE_PRIVATE)
                            prefs.edit().apply {
                                putInt("PREMIUM_HOURS", newHours)
                                putLong("LAST_PREMIUM_SYNC_AT", lastPremiumSyncAt.value)
                                apply()
                            }
                            
                            if (newHours == 0) {
                                isPro.value = false
                                workSecs.value = 25 * 60
                                shortBreakSecs.value = 5 * 60
                                longBreakSecs.value = 10 * 60
                                sessionsPerCycle.value = 4
                                prefs.edit().putBoolean("IS_PRO", false).apply()
                            }
                            
                            val sub = googleUserSub.value
                            if (sub != null) {
                                launch(Dispatchers.IO) {
                                    syncUserHoursToSupabase(sub, newHours)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    private suspend fun syncUserHoursToSupabase(sub: String, hours: Int) {
        var attempts = 0
        val maxAttempts = 3
        var success = false
        
        while (attempts < maxAttempts && !success) {
            attempts++
            var conn: java.net.HttpURLConnection? = null
            try {
                val url = java.net.URL("https://nqshkkzrnsafnfvujanr.supabase.co/rest/v1/users?google_sub=eq.$sub")
                conn = url.openConnection() as java.net.HttpURLConnection
                conn.requestMethod = "PATCH"
                conn.connectTimeout = 10000
                conn.readTimeout = 10000
                conn.setRequestProperty("apikey", "sb_publishable_O-jmtJ8nx11HO0kR8D7mzw_uVsyRqFq")
                conn.setRequestProperty("Authorization", "Bearer sb_publishable_O-jmtJ8nx11HO0kR8D7mzw_uVsyRqFq")
                conn.setRequestProperty("Content-Type", "application/json")
                conn.doOutput = true
                
                val jsonBody = """
                    {
                        "premium_hours": $hours,
                        "last_premium_sync_at": "now()",
                        "platform": "Mobile"
                    }
                """.trimIndent()
                
                java.io.OutputStreamWriter(conn.outputStream).use { writer ->
                    writer.write(jsonBody)
                    writer.flush()
                }
                
                val responseCode = conn.responseCode
                if (responseCode in 200..299) {
                    success = true
                } else {
                    val errorText = conn.errorStream?.bufferedReader()?.use { it.readText() } ?: ""
                    android.util.Log.e("Supabase", "syncUserHoursToSupabase failed on attempt $attempts with code $responseCode: $errorText")
                    if (responseCode in 400..499 && responseCode != 429) {
                        break
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("Supabase", "syncUserHoursToSupabase exception on attempt $attempts: ${e.message}", e)
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
    }

    private fun loadPreferences() {
        val prefs = getSharedPreferences("GoofyFocusPrefs", Context.MODE_PRIVATE)
        val permanentPro = prefs.getBoolean("IS_PRO", false)
        val expiry = prefs.getLong("PRO_EXPIRY_TIME", 0L)
        proExpiryTime.value = expiry
        
        googleUserSub.value = prefs.getString("GOOGLE_USER_SUB", null)
        googleUserEmail.value = prefs.getString("GOOGLE_USER_EMAIL", null)
        googleUserName.value = prefs.getString("GOOGLE_USER_NAME", null)
        googleUserPicture.value = prefs.getString("GOOGLE_USER_PICTURE", null)
        premiumDuration.value = prefs.getString("PREMIUM_DURATION", null)
        
        val pHours = prefs.getInt("PREMIUM_HOURS", 0)
        val pSync = prefs.getLong("LAST_PREMIUM_SYNC_AT", 0L)
        premiumHours.value = pHours
        lastPremiumSyncAt.value = pSync
        
        if (permanentPro || expiry > System.currentTimeMillis()) {
            isPro.value = true
        } else if (pHours > 0) {
            if (pSync > 0L) {
                val elapsedMillis = System.currentTimeMillis() - pSync
                val elapsedHours = (elapsedMillis / (3600 * 1000L)).toInt()
                if (elapsedHours > 0) {
                    val remaining = Math.max(0, pHours - elapsedHours)
                    premiumHours.value = remaining
                    lastPremiumSyncAt.value = pSync + elapsedHours * 3600 * 1000L
                    
                    prefs.edit().apply {
                        putInt("PREMIUM_HOURS", remaining)
                        putLong("LAST_PREMIUM_SYNC_AT", lastPremiumSyncAt.value)
                        apply()
                    }
                    
                    if (remaining == 0) {
                        isPro.value = false
                        prefs.edit().putBoolean("IS_PRO", false).apply()
                    } else {
                        isPro.value = true
                    }
                } else {
                    isPro.value = true
                }
            } else {
                isPro.value = true
            }
        } else {
            isPro.value = false
        }
        
        customGifUri.value = prefs.getString("CUSTOM_GIF_URI", null)
        mascotType.value = prefs.getString("MASCOT_TYPE", "cat") ?: "cat"
        
        // Load focus levels and XP
        focusXp.value = prefs.getInt("FOCUS_XP", 0)
        focusLevel.value = prefs.getInt("FOCUS_LEVEL", 1)
        
        // Load custom settings if Pro, else force standard defaults
        if (isPro.value) {
            workSecs.value = prefs.getInt("WORK_SECS", 25 * 60)
            shortBreakSecs.value = prefs.getInt("SHORT_BREAK_SECS", 5 * 60)
            longBreakSecs.value = prefs.getInt("LONG_BREAK_SECS", 15 * 60)
            sessionsPerCycle.value = prefs.getInt("SESSIONS_PER_CYCLE", 4)
        } else {
            workSecs.value = 25 * 60
            shortBreakSecs.value = 5 * 60
            longBreakSecs.value = 10 * 60
            sessionsPerCycle.value = 4
        }
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
            addXp(this, 20) // Award +20 XP on work session completion
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
            .setSmallIcon(R.drawable.ic_notification)
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
            .setSmallIcon(R.drawable.ic_notification)
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
        
        // Focus Levels & Progression (Emotional Design)
        val focusXp = MutableStateFlow(0)
        val focusLevel = MutableStateFlow(1)
        val levelUpEvent = kotlinx.coroutines.flow.MutableSharedFlow<Int>(extraBufferCapacity = 1)
        var lastXpClickTime = 0L

        fun addXp(context: Context, amount: Int): Boolean {
            val currentXp = focusXp.value + amount
            focusXp.value = currentXp
            
            var leveledUp = false
            var currentLevel = focusLevel.value
            while (currentXp >= currentLevel * 100) {
                currentLevel += 1
                leveledUp = true
            }
            
            if (leveledUp) {
                focusLevel.value = currentLevel
                levelUpEvent.tryEmit(currentLevel)
            }
            
            val prefs = context.getSharedPreferences("GoofyFocusPrefs", Context.MODE_PRIVATE)
            prefs.edit().apply {
                putInt("FOCUS_XP", focusXp.value)
                putInt("FOCUS_LEVEL", focusLevel.value)
                apply()
            }
            return leveledUp
        }

        // Settings (in seconds)
        val workSecs = MutableStateFlow(25 * 60)
        val shortBreakSecs = MutableStateFlow(5 * 60)
        val longBreakSecs = MutableStateFlow(15 * 60)
        val sessionsPerCycle = MutableStateFlow(4)
        val breakFlow = MutableStateFlow("auto")

        // Premium State Flows
        val isPro = MutableStateFlow(false)
        val proExpiryTime = MutableStateFlow(0L)
        val customGifUri = MutableStateFlow<String?>(null)
        val mascotType = MutableStateFlow("cat") // cat, dog

        val googleUserSub = MutableStateFlow<String?>(null)
        val googleUserEmail = MutableStateFlow<String?>(null)
        val googleUserName = MutableStateFlow<String?>(null)
        val googleUserPicture = MutableStateFlow<String?>(null)
        val premiumDuration = MutableStateFlow<String?>(null)
        val premiumHours = MutableStateFlow(0)
        val lastPremiumSyncAt = MutableStateFlow(0L)

        fun signInUser(context: Context, sub: String, email: String, name: String?, picture: String?, duration: String?) {
            googleUserSub.value = sub
            googleUserEmail.value = email
            googleUserName.value = name
            googleUserPicture.value = picture
            premiumDuration.value = duration
            
            val prefs = context.getSharedPreferences("GoofyFocusPrefs", Context.MODE_PRIVATE)
            prefs.edit().apply {
                putString("GOOGLE_USER_SUB", sub)
                putString("GOOGLE_USER_EMAIL", email)
                putString("GOOGLE_USER_NAME", name)
                putString("GOOGLE_USER_PICTURE", picture)
                putString("PREMIUM_DURATION", duration)
                apply()
            }
        }

        fun signInUserWithHours(context: Context, sub: String, email: String, name: String?, picture: String?, hours: Int, syncTime: Long) {
            googleUserSub.value = sub
            googleUserEmail.value = email
            googleUserName.value = name
            googleUserPicture.value = picture
            premiumHours.value = hours
            lastPremiumSyncAt.value = syncTime
            isPro.value = true
            
            val prefs = context.getSharedPreferences("GoofyFocusPrefs", Context.MODE_PRIVATE)
            prefs.edit().apply {
                putString("GOOGLE_USER_SUB", sub)
                putString("GOOGLE_USER_EMAIL", email)
                putString("GOOGLE_USER_NAME", name)
                putString("GOOGLE_USER_PICTURE", picture)
                putInt("PREMIUM_HOURS", hours)
                putLong("LAST_PREMIUM_SYNC_AT", syncTime)
                putBoolean("IS_PRO", true)
                apply()
            }
        }

        fun purchasePremiumHours(context: Context, hoursToAdd: Int) {
            val currentHours = premiumHours.value
            val newHours = currentHours + hoursToAdd
            premiumHours.value = newHours
            lastPremiumSyncAt.value = System.currentTimeMillis()
            isPro.value = newHours > 0
            
            val prefs = context.getSharedPreferences("GoofyFocusPrefs", Context.MODE_PRIVATE)
            prefs.edit().apply {
                putInt("PREMIUM_HOURS", newHours)
                putLong("LAST_PREMIUM_SYNC_AT", lastPremiumSyncAt.value)
                putBoolean("IS_PRO", newHours > 0)
                apply()
            }
        }

        fun signOutUser(context: Context) {
            googleUserSub.value = null
            googleUserEmail.value = null
            googleUserName.value = null
            googleUserPicture.value = null
            premiumDuration.value = null
            premiumHours.value = 0
            lastPremiumSyncAt.value = 0L
            setProEnabled(context, false)
            
            val prefs = context.getSharedPreferences("GoofyFocusPrefs", Context.MODE_PRIVATE)
            prefs.edit().apply {
                remove("GOOGLE_USER_SUB")
                remove("GOOGLE_USER_EMAIL")
                remove("GOOGLE_USER_NAME")
                remove("GOOGLE_USER_PICTURE")
                remove("PREMIUM_DURATION")
                remove("PREMIUM_HOURS")
                remove("LAST_PREMIUM_SYNC_AT")
                apply()
            }
        }

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

        fun grant24HourPass(context: Context) {
            val newExpiry = System.currentTimeMillis() + 24 * 60 * 60 * 1000L
            proExpiryTime.value = newExpiry
            isPro.value = true
            val prefs = context.getSharedPreferences("GoofyFocusPrefs", Context.MODE_PRIVATE)
            prefs.edit().putLong("PRO_EXPIRY_TIME", newExpiry).apply()
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
