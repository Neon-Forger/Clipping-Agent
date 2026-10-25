package com.neonforger.clipcartel

import android.content.Context
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.TimeUnit

/** Checks ntfy for new agent messages every 15 minutes (the shortest Android allows)
 *  and shows them as notifications, even when the app is closed. */
class PollWorker(ctx: Context, params: WorkerParameters) : Worker(ctx, params) {

    override fun doWork(): Result {
        val p = Prefs.get(applicationContext)
        val topic = p.getString("topic", "") ?: ""
        if (topic.isBlank() || !p.getBoolean("notify", true)) return Result.success()
        val server = p.getString("server", "https://ntfy.sh") ?: "https://ntfy.sh"
        val token = p.getString("token", "") ?: ""
        val last = p.getString("lastId", "") ?: ""
        val since = if (last.isBlank()) "20m" else last
        return try {
            val conn = URL("$server/$topic/json?poll=1&since=$since").openConnection() as HttpURLConnection
            conn.connectTimeout = 15000
            conn.readTimeout = 30000
            if (token.isNotBlank()) conn.setRequestProperty("Authorization", "Bearer $token")
            val body = conn.inputStream.bufferedReader().readText()
            var newest = last
            body.lineSequence().filter { it.isNotBlank() }.forEach { line ->
                val m = JSONObject(line)
                if (m.optString("event") != "message") return@forEach
                newest = m.optString("id", newest)
                val title = m.optString("title", "NeonClip")
                if (title.startsWith("__")) return@forEach
                Notifier.show(applicationContext, m.optString("id").hashCode(), title,
                    m.optString("message"), m.optInt("priority", 3))
            }
            if (newest.isNotBlank()) p.edit().putString("lastId", newest).apply()
            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }

    companion object {
        fun schedule(ctx: Context) {
            val req = PeriodicWorkRequestBuilder<PollWorker>(15, TimeUnit.MINUTES)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .build()
            WorkManager.getInstance(ctx).enqueueUniquePeriodicWork("poll", ExistingPeriodicWorkPolicy.UPDATE, req)
        }
    }
}
