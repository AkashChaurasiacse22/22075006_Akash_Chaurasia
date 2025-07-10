package com.example.test1

import android.app.Service
import android.content.Intent
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.Log
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.util.*
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

class MCPService : Service() {

    private val client = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.MILLISECONDS) // No read timeout for SSE
        .build()

    private val executor = Executors.newSingleThreadExecutor()
    private val mcpUrl = "http://10.0.2.2:8000/mcp/"

    private var requestId = ""

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        requestId = UUID.randomUUID().toString()
        sendRequestAndListenToSSE()
        return START_STICKY
    }

    private fun sendRequestAndListenToSSE() {
        val json = JSONObject().apply {
            put("jsonrpc", "2.0")
            put("id", requestId)
            put("method", "tools/list")
            put("params", JSONObject())
        }

        val body = RequestBody.create(
            "application/json".toMediaTypeOrNull(),
            json.toString()
        )

        val post = Request.Builder()
            .url(mcpUrl)
            .post(body)
            .build()

        client.newCall(post).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e("MCPService", "❌ POST failed: ${e.message}")
            }

            override fun onResponse(call: Call, response: Response) {
                Log.d("MCPService", "✅ POST sent with id=$requestId")

                // Delay SSE connection to allow server to write response to stream
                Handler(Looper.getMainLooper()).postDelayed({
                    listenToSSE(requestId)
                }, 300) // 300ms delay
            }
        })
    }

    private fun listenToSSE(expectedId: String) {
        val request = Request.Builder()
            .url(mcpUrl)
            .get()
            .build()

        executor.execute {
            try {
                client.newCall(request).execute().use { response ->
                    if (!response.isSuccessful) {
                        Log.e("MCPService", "❌ SSE connection failed: ${response.code}")
                        return@execute
                    }

                    val reader = BufferedReader(InputStreamReader(response.body?.byteStream()))
                    val dataBuilder = StringBuilder()

                    var event: String? = null
                    var matched = false

                    reader.forEachLine { line ->
                        if (matched) return@forEachLine

                        when {
                            line.startsWith("event:") -> {
                                event = line.removePrefix("event:").trim()
                            }
                            line.startsWith("data:") -> {
                                dataBuilder.append(line.removePrefix("data:").trim())
                            }
                            line.isEmpty() -> {
                                val jsonStr = dataBuilder.toString()
                                if (jsonStr.isNotEmpty()) {
                                    val json = JSONObject(jsonStr)
                                    val id = json.optString("id", "")

                                    if (id == expectedId) {
                                        matched = true
                                        Log.i("MCPService", "✅ Matched SSE response: $jsonStr")
                                        // TODO: Process this response
                                    } else {
                                        Log.d("MCPService", "Ignored SSE with id=$id")
                                    }
                                }
                                dataBuilder.setLength(0)
                            }
                        }
                    }
                }
            } catch (e: Exception) {
                Log.e("MCPService", "❌ SSE Exception: ${e.message}")
            }
        }
    }

    override fun onDestroy() {
        executor.shutdownNow()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
