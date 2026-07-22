package com.arunkumar.goofyfocus.notification

import android.content.Context
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

object DailyNotificationScheduler {

    private const val WORK_NAME = "DailyFocusReminderWork"

    fun scheduleDailyNotifications(context: Context) {
        // Schedule worker every 12 hours to issue notifications 2 times per day
        val dailyNotificationRequest = PeriodicWorkRequestBuilder<DailyNotificationWorker>(
            12, TimeUnit.HOURS
        ).build()

        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            WORK_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            dailyNotificationRequest
        )
    }
}
