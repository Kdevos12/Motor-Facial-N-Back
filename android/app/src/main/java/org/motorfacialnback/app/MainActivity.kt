package org.motorfacialnback.app

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.graphics.Color
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.widget.FrameLayout
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

class MainActivity : Activity() {
    private val mainHandler = Handler(Looper.getMainLooper())
    private var webView: WebView? = null
    private var pendingCameraRequest: PermissionRequest? = null
    private lateinit var statusText: TextView
    private var trainingActive = false

    inner class AppBridge {
        @JavascriptInterface
        fun setTrainingActive(active: Boolean) {
            mainHandler.post {
                trainingActive = active
                updateKeepScreenOn()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        window.statusBarColor = Color.rgb(15, 18, 24)
        window.navigationBarColor = Color.rgb(15, 18, 24)
        showStartup()
        startLocalServer()
    }

    private fun showStartup() {
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setBackgroundColor(Color.rgb(15, 18, 24))
            setPadding(32, 32, 32, 32)
        }
        val title = TextView(this).apply {
            text = "Motor & Facial N-Back"
            textSize = 23f
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
        }
        val progress = ProgressBar(this).apply {
            isIndeterminate = true
            val params = LinearLayout.LayoutParams(52, 52)
            params.topMargin = 24
            layoutParams = params
        }
        statusText = TextView(this).apply {
            text = "Starting your private training space…"
            textSize = 15f
            setTextColor(Color.LTGRAY)
            gravity = Gravity.CENTER
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT,
            )
            params.topMargin = 18
            layoutParams = params
        }
        layout.addView(title)
        layout.addView(progress)
        layout.addView(statusText)
        fitSystemBars(layout)
        setContentView(layout)
    }

    private fun fitSystemBars(view: View) {
        val left = view.paddingLeft
        val top = view.paddingTop
        val right = view.paddingRight
        val bottom = view.paddingBottom
        ViewCompat.setOnApplyWindowInsetsListener(view) { target, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            target.setPadding(left + bars.left, top + bars.top, right + bars.right, bottom + bars.bottom)
            insets
        }
    }

    private fun startLocalServer() {
        try {
            val webDirectory = File(filesDir, "web")
            copyBundledWebFiles(webDirectory)
            if (!Python.isStarted()) Python.start(AndroidPlatform(this))
            thread(name = "mfnb-local-server") {
                try {
                    Python.getInstance()
                        .getModule("mfnb.android_server")
                        .callAttr("start", File(filesDir, "mfnb").absolutePath, webDirectory.absolutePath)
                } catch (error: Exception) {
                    mainHandler.post { showFailure(error.message ?: error.javaClass.simpleName) }
                }
            }
            waitForServer()
        } catch (error: Exception) {
            showFailure(error.message ?: error.javaClass.simpleName)
        }
    }

    private fun copyBundledWebFiles(target: File) {
        fun copyDirectory(assetPath: String, destination: File) {
            destination.mkdirs()
            assets.list(assetPath).orEmpty().forEach { name ->
                val childPath = "$assetPath/$name"
                val child = File(destination, name)
                val children = assets.list(childPath).orEmpty()
                if (children.isNotEmpty()) {
                    copyDirectory(childPath, child)
                } else {
                    assets.open(childPath).use { input -> child.outputStream().use(input::copyTo) }
                }
            }
        }
        copyDirectory("web", target)
    }

    private fun waitForServer() {
        thread(name = "mfnb-server-check") {
            var lastError: String? = null
            repeat(240) {
                try {
                    val connection = URL("http://127.0.0.1:8765/api/meta").openConnection() as HttpURLConnection
                    connection.connectTimeout = 1_000
                    connection.readTimeout = 1_000
                    if (connection.responseCode == HttpURLConnection.HTTP_OK) {
                        connection.disconnect()
                        mainHandler.post { showApp() }
                        return@thread
                    }
                    lastError = "Local server returned HTTP ${connection.responseCode}."
                    connection.disconnect()
                } catch (error: Exception) {
                    lastError = error.message
                }
                Thread.sleep(500)
            }
            mainHandler.post { showFailure(lastError ?: "The local server did not start.") }
        }
    }

    private fun showApp() {
        val view = WebView(this)
        webView = view
        view.setBackgroundColor(Color.rgb(15, 18, 24))
        view.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            mediaPlaybackRequiresUserGesture = false
            allowFileAccess = false
            allowContentAccess = false
        }
        view.addJavascriptInterface(AppBridge(), "AndroidApp")
        view.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                if (request.url.host in setOf("127.0.0.1", "localhost")) return false
                val uri = request.url
                if (request.isForMainFrame && uri.scheme in setOf("https", "http")) {
                    startActivity(Intent(Intent.ACTION_VIEW, uri))
                }
                return true
            }
        }
        view.webChromeClient = object : WebChromeClient() {
            override fun onPermissionRequest(request: PermissionRequest) {
                val camera = PermissionRequest.RESOURCE_VIDEO_CAPTURE
                val requested = request.resources.filter { it == camera }.toTypedArray()
                if (requested.isEmpty() || request.origin.host !in setOf("127.0.0.1", "localhost")) {
                    request.deny()
                    return
                }
                if (ContextCompat.checkSelfPermission(this@MainActivity, Manifest.permission.CAMERA)
                    == PackageManager.PERMISSION_GRANTED) {
                    request.grant(requested)
                } else {
                    pendingCameraRequest = request
                    ActivityCompat.requestPermissions(
                        this@MainActivity,
                        arrayOf(Manifest.permission.CAMERA),
                        CAMERA_PERMISSION_REQUEST,
                    )
                }
            }
        }
        val content = FrameLayout(this).apply {
            setBackgroundColor(Color.rgb(15, 18, 24))
            addView(view, FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT,
            ))
        }
        fitSystemBars(content)
        setContentView(content)
        view.loadUrl("http://127.0.0.1:8765/")
    }

    private fun showFailure(message: String) {
        statusText.text = "Could not start the app:\n$message\n\nClose and reopen the app to retry."
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, results: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, results)
        if (requestCode == CAMERA_PERMISSION_REQUEST) {
            val request = pendingCameraRequest
            pendingCameraRequest = null
            if (results.firstOrNull() == PackageManager.PERMISSION_GRANTED && request != null) {
                request.grant(arrayOf(PermissionRequest.RESOURCE_VIDEO_CAPTURE))
            } else {
                request?.deny()
            }
        }
    }

    @Suppress("DEPRECATION")
    override fun onBackPressed() {
        if (webView?.canGoBack() == true) webView?.goBack() else super.onBackPressed()
    }

    override fun onDestroy() {
        window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        webView?.destroy()
        webView = null
        super.onDestroy()
    }

    override fun onPause() {
        window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        super.onPause()
    }

    override fun onResume() {
        super.onResume()
        updateKeepScreenOn()
    }

    private fun updateKeepScreenOn() {
        if (trainingActive && !isFinishing) {
            window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        } else {
            window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
    }

    companion object {
        private const val CAMERA_PERMISSION_REQUEST = 24
    }
}
