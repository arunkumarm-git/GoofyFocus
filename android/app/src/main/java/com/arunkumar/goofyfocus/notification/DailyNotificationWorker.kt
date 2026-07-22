package com.arunkumar.goofyfocus.notification

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.arunkumar.goofyfocus.MainActivity
import com.arunkumar.goofyfocus.R
import kotlin.random.Random

class DailyNotificationWorker(
    private val context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return try {
            sendDailyFocusNotification()
            Result.success()
        } catch (e: Exception) {
            android.util.Log.e("DailyNotificationWorker", "Error posting daily notification", e)
            Result.retry()
        }
    }

    private fun sendDailyFocusNotification() {
        val channelId = "daily_focus_reminders"
        val notificationManager =
            context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channelName = "Daily Focus Reminders"
            val channelDescription = "Twice daily notifications to keep you productive and rested."
            val channel = NotificationChannel(
                channelId,
                channelName,
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = channelDescription
            }
            notificationManager.createNotificationChannel(channel)
        }

        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        val pendingIntent = PendingIntent.getActivity(
            context,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val messages = listOf(
            Pair("Stay Focused with GoofyFocus 🎯", "Time for a productive session! Ready to accomplish your goals today?"),
            Pair("Time for a Quick Refresh ☕", "Remember to take timely breaks to maintain high mental performance."),
            Pair("Keep Up Your Focus Momentum 🚀", "Small, focused timer blocks lead to big results. Start a session now!"),
            Pair("Mindful Focus & Reset 🧠", "Eliminate distractions and track your deep work with GoofyFocus.")
        )

        val selected = messages[Random.nextInt(messages.size)]

        val notification = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(selected.first)
            .setContentText(selected.second)
            .setStyle(NotificationCompat.BigTextStyle().bigText(selected.second))
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build()

        val notificationId = (System.currentTimeMillis() % 10000).toInt()
        notificationManager.notify(notificationId, notification)
    }
}
