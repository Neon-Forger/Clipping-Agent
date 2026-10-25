package com.neonforger.clipcartel

import android.annotation.SuppressLint
import android.app.Activity
import android.app.AlertDialog
import android.graphics.Color
import android.os.Bundle
import android.util.Base64
import android.view.Gravity
import android.view.ViewGroup
import android.webkit.CookieManager
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.webkit.WebSettingsCompat
import androidx.webkit.WebViewFeature
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

/** Sign in to a site on the phone, then send the sign-in (cookies) to the PC agent,
 *  encrypted with the pairing code so nobody reading the ntfy topic can use it. */
class LoginActivity : Activity() {

    companion object {
        // Same user agent as the PC agent's browser, so the site sees one consistent "computer".
        const val DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"

        val SITES = mapOf(
            "tiktok" to Triple("TikTok", "https://www.tiktok.com/login", listOf("https://www.tiktok.com/", "https://tiktok.com/", "https://www.tiktok.com/tiktokstudio/")),
            "contentrewards" to Triple("Content Rewards", "https://contentrewards.com/login", listOf("https://contentrewards.com/", "https://www.contentrewards.com/", "https://contentrewards.com/c/")),
            "youtube" to Triple("YouTube", "https://accounts.google.com/ServiceLogin?service=youtube&continue=https%3A%2F%2Fwww.youtube.com%2F", listOf("https://www.youtube.com/", "https://youtube.com/"))
        )
    }

    private lateinit var web: WebView
    private lateinit var service: String

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        service = intent.getStringExtra("service") ?: "tiktok"
        val site = SITES[service] ?: SITES["tiktok"]!!

        val root = LinearLayout(this)
        root.orientation = LinearLayout.VERTICAL
        root.setBackgroundColor(Color.parseColor("#040915"))

        val bar = LinearLayout(this)
        bar.orientation = LinearLayout.HORIZONTAL
        bar.gravity = Gravity.CENTER_VERTICAL
        bar.setPadding(24, 18, 18, 18)
        val title = TextView(this)
        title.text = "Sign in to ${site.first}"
        title.setTextColor(Color.WHITE)
        title.textSize = 16f
        bar.addView(title, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        val send = Button(this)
        send.text = "Done · send to PC"
        send.setBackgroundColor(Color.parseColor("#FF2BD6"))
        send.setTextColor(Color.WHITE)
        send.setOnClickListener { sendToPc(site) }
        bar.addView(send)
        root.addView(bar)

        val hint = TextView(this)
        hint.text = if (service == "tiktok")
            "No password? Tap “Use phone / email / username” → Phone → “Log in with code”, or use the QR code button in the PC app. " +
                    "When you see your account, tap “Done · send to PC”."
        else
            "Sign in below (pinch to zoom). When you see your account, tap “Done · send to PC”. " +
                    "Use email + a code if you can; “Continue with Google” is often blocked inside apps."
        hint.setTextColor(Color.parseColor("#8AA0C4"))
        hint.textSize = 12f
        hint.setPadding(24, 0, 24, 12)
        root.addView(hint)

        web = WebView(this)
        val s = web.settings
        s.javaScriptEnabled = true
        s.domStorageEnabled = true
        s.userAgentString = DESKTOP_UA
        s.useWideViewPort = true
        s.loadWithOverviewMode = true
        s.builtInZoomControls = true
        s.displayZoomControls = false
        s.setSupportMultipleWindows(false)
        if (WebViewFeature.isFeatureSupported(WebViewFeature.REQUESTED_WITH_HEADER_ALLOW_LIST)) {
            WebSettingsCompat.setRequestedWithHeaderOriginAllowList(s, emptySet())
        }
        CookieManager.getInstance().setAcceptCookie(true)
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, true)
        web.webViewClient = WebViewClient()
        web.webChromeClient = WebChromeClient()
        root.addView(web, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        setContentView(root)
        web.loadUrl(site.second)
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (web.canGoBack()) web.goBack() else super.onBackPressed()
    }

    private fun collectCookies(urls: List<String>): String {
        val cm = CookieManager.getInstance()
        cm.flush()
        val jar = LinkedHashMap<String, String>()
        for (u in urls) {
            val c = cm.getCookie(u) ?: continue
            for (part in c.split(";")) {
                val p = part.trim()
                val i = p.indexOf('=')
                if (i > 0) jar[p.substring(0, i)] = p.substring(i + 1)
            }
        }
        return jar.entries.joinToString("; ") { it.key + "=" + it.value }
    }

    private fun sendToPc(site: Triple<String, String, List<String>>) {
        val p = Prefs.get(this)
        val topic = p.getString("topic", "") ?: ""
        val pair = p.getString("pair", "") ?: ""
        if (topic.isBlank() || pair.isBlank()) {
            AlertDialog.Builder(this).setMessage("Enter the topic and pairing code from the PC app first (Settings → Change server / topic).")
                .setPositiveButton("OK", null).show()
            return
        }
        val cookies = collectCookies(site.third)
        if (cookies.isBlank()) {
            Toast.makeText(this, "Not signed in yet. Finish signing in first.", Toast.LENGTH_LONG).show()
            return
        }
        val payload = JSONObject().put("service", service).put("cookies", cookies).put("ua", DESKTOP_UA).toString()
        val blob = encrypt(payload, pair)
        val server = p.getString("server", "https://ntfy.sh") ?: "https://ntfy.sh"
        val token = p.getString("token", "") ?: ""
        Toast.makeText(this, "Sending to your PC...", Toast.LENGTH_SHORT).show()
        Thread {
            val ok = try {
                val conn = URL("$server/$topic-cmd").openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.doOutput = true
                conn.connectTimeout = 15000
                conn.readTimeout = 30000
                if (token.isNotBlank()) conn.setRequestProperty("Authorization", "Bearer $token")
                conn.outputStream.use { it.write(("login $blob").toByteArray()) }
                conn.responseCode in 200..299
            } catch (e: Exception) {
                false
            }
            runOnUiThread {
                if (ok) {
                    Toast.makeText(this, "Sent ✓ Watch for the “sign-in” notification from your PC.", Toast.LENGTH_LONG).show()
                    finish()
                } else {
                    Toast.makeText(this, "Couldn't reach ntfy. Check your connection and try again.", Toast.LENGTH_LONG).show()
                }
            }
        }.start()
    }

    private fun encrypt(text: String, code: String): String {
        val norm = code.uppercase().filter { it.isLetterOrDigit() }
        val key = MessageDigest.getInstance("SHA-256").digest(("clipcartel:$norm").toByteArray())
        val nonce = ByteArray(12).also { SecureRandom().nextBytes(it) }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(128, nonce))
        val ct = cipher.doFinal(text.toByteArray())
        return Base64.encodeToString(nonce + ct, Base64.NO_WRAP)
    }
}
