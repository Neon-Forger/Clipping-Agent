package com.neonforger.clipcartel

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import org.json.JSONObject

class MainActivity : Activity() {
    private lateinit var web: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        web = WebView(this)
        web.setBackgroundColor(0xFF0B0B0C.toInt())
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        web.settings.allowFileAccess = true
        web.addJavascriptInterface(Bridge(), "Android")
        web.webChromeClient = WebChromeClient()
        web.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val url = request.url.toString()
                if (url.startsWith("http")) {
                    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                    return true
                }
                return false
            }
        }
        setContentView(web)
        web.loadUrl("file:///android_asset/index.html")

        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        }
        Notifier.ensureChannel(this)
        PollWorker.schedule(this)
    }

    override fun onResume() {
        super.onResume()
        if (::web.isInitialized) web.evaluateJavascript("window.onAppResume && window.onAppResume()", null)
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (web.canGoBack()) web.goBack() else super.onBackPressed()
    }

    inner class Bridge {
        @JavascriptInterface
        fun getConfig(): String {
            val p = Prefs.get(this@MainActivity)
            return JSONObject()
                .put("server", p.getString("server", "https://ntfy.sh"))
                .put("topic", p.getString("topic", ""))
                .put("token", p.getString("token", ""))
                .put("notify", p.getBoolean("notify", true))
                .toString()
        }

        @JavascriptInterface
        fun saveConfig(server: String, topic: String, token: String, notify: Boolean) {
            Prefs.get(this@MainActivity).edit()
                .putString("server", server.trim().trimEnd('/'))
                .putString("topic", topic.trim())
                .putString("token", token.trim())
                .putBoolean("notify", notify)
                .putString("lastId", "")
                .apply()
            PollWorker.schedule(this@MainActivity)
        }

        @JavascriptInterface
        fun setLastSeen(id: String) {
            Prefs.get(this@MainActivity).edit().putString("lastId", id).apply()
        }

        @JavascriptInterface
        fun openUrl(url: String) {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        }

        @JavascriptInterface
        fun version(): String = BuildConfig.VERSION_NAME
    }
}
