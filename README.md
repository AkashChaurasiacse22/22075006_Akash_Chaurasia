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

    private var currentRequestId: String = ""
    private var currentCall: Call? = null

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
                    Log.d("MCPService", "POST succeeded with id: $currentRequestId")
                    // Cancel any previous SSE listener
                    currentCall?.cancel()
                    listenToSSE(currentRequestId)
                } else {
                    Log.e("MCPService", "POST request error: ${response.code}")
                }
            }
        })
    }

    private fun listenToSSE(requestId: String) {
        val getRequest = Request.Builder()
            .url(mcpUrl)
            .get()
            .build()

        executor.execute {
            try {
                val call = client.newCall(getRequest)
                currentCall = call

                call.execute().use { response ->
                    if (!response.isSuccessful) {
                        Log.e("MCPService", "SSE connection failed: $response")
                        return@execute
                    }

                    val reader = BufferedReader(InputStreamReader(response.body?.byteStream()))
                    var line: String?
                    var event: String? = null
                    val dataBuilder = StringBuilder()

                    while (reader.readLine().also { line = it } != null && !call.isCanceled()) {
                        line = line?.trim()

                        if (line!!.startsWith("event:")) {
                            event = line!!.removePrefix("event:").trim()
                        } else if (line!!.startsWith("data:")) {
                            dataBuilder.append(line!!.removePrefix("data:").trim())
                        } else if (line!!.isEmpty()) {
                            val fullData = dataBuilder.toString()
                            if (event != null && fullData.isNotEmpty()) {
                                val json = JSONObject(fullData)
                                val incomingId = json.optString("id", "")

                                if (incomingId == requestId) {
                                    Log.i("MCPService", "✅ SSE matched [$event]: $fullData")
                                    // Optional: stop listening after matching event
                                    call.cancel()
                                } else {
                                    Log.i("MCPService", "❌ SSE ignored id=$incomingId (expected $requestId)")
                                }
                            }
                            // Reset
                            event = null
                            dataBuilder.setLength(0)
                        }
                    }
                }
            } catch (e: Exception) {
                Log.e("MCPService", "SSE Error: ${e.message}")
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
