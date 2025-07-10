package com.example.test1

import android.app.Service
import android.content.Intent
import android.os.IBinder
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
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    private val executor = Executors.newSingleThreadExecutor()
    private val mcpUrl = "http://10.0.2.2:8000/mcp/"
    private var currentCall: Call? = null
    private var currentRequestId = ""

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        sendJsonRequestThenListen()
        return START_STICKY
    }

    private fun sendJsonRequestThenListen() {
        currentRequestId = UUID.randomUUID().toString()

        val jsonRequest = JSONObject().apply {
            put("jsonrpc", "2.0")
            put("id", currentRequestId)
            put("method", "tools/list")
            put("params", JSONObject())
        }

        val requestBody = RequestBody.create(
            "application/json".toMediaTypeOrNull(),
            jsonRequest.toString()
        )

        val postRequest = Request.Builder()
            .url(mcpUrl)
            .post(requestBody)
            .build()

        client.newCall(postRequest).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e("MCPService", "POST request failed: ${e.message}")
            }

            override fun onResponse(call: Call, response: Response) {
                if (response.isSuccessful) {
                    Log.d("MCPService", "✅ POST succeeded for id=$currentRequestId")

                    // Slight delay to allow server to prepare the SSE buffer
                    executor.execute {
                        Thread.sleep(500) // Delay to let server write response
                        currentCall?.cancel()
                        listenToSSE(currentRequestId)
                    }
                } else {
                    Log.e("MCPService", "❌ POST failed with code ${response.code}")
                }
            }
        })
    }

    private fun listenToSSE(requestId: String) {
        val getRequest = Request.Builder()
            .url(mcpUrl)
            .get()
            .build()

        val call = client.newCall(getRequest)
        currentCall = call

        executor.execute {
            try {
                call.execute().use { response ->
                    if (!response.isSuccessful) {
                        Log.e("MCPService", "SSE connection failed: ${response.code}")
                        return@execute
                    }

                    val reader = BufferedReader(InputStreamReader(response.body?.byteStream()))
                    var line: String?
                    var event: String? = null
                    val dataBuilder = StringBuilder()

                    while (reader.readLine().also { line = it } != null && !call.isCanceled()) {
                        val trimmedLine = line!!.trim()
                        when {
                            trimmedLine.startsWith("event:") -> {
                                event = trimmedLine.removePrefix("event:").trim()
                            }
                            trimmedLine.startsWith("data:") -> {
                                dataBuilder.append(trimmedLine.removePrefix("data:").trim())
                            }
                            trimmedLine.isEmpty() -> {
                                val fullData = dataBuilder.toString()
                                if (fullData.isNotEmpty() && event != null) {
                                    val json = JSONObject(fullData)
                                    val incomingId = json.optString("id", "")

                                    if (incomingId == requestId) {
                                        Log.i("MCPService", "✅ Matched SSE [$event] for id=$incomingId: $fullData")
                                        // TODO: Handle the correct SSE response here
                                        call.cancel() // stop reading more after matched one
                                    } else {
                                        Log.i("MCPService", "🔁 Ignored SSE [$event] for id=$incomingId (expected $requestId)")
                                    }
                                }
                                event = null
                                dataBuilder.setLength(0)
                            }
                        }
                    }
                }
            } catch (e: Exception) {
                if (!call.isCanceled()) {
                    Log.e("MCPService", "SSE error: ${e.message}")
                }
            }
        }
    }

    override fun onDestroy() {
        currentCall?.cancel()
        executor.shutdownNow()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
