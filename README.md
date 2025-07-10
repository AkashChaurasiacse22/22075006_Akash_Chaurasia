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
import java.io.IOException
import java.util.*
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

class MCPService : Service() {

    private val client = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.MILLISECONDS) // keep-alive for SSE
        .build()

    private val executor = Executors.newSingleThreadExecutor()
    private val mcpUrl = "http://10.0.2.2:8000/mcp/"
    private lateinit var requestId: String

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        requestId = UUID.randomUUID().toString()
        sendJsonRpcAndStreamSse()
        return START_STICKY
    }

    private fun sendJsonRpcAndStreamSse() {
        // 1) Build JSON-RPC request
        val rpc = JSONObject().apply {
            put("jsonrpc", "2.0")
            put("id", requestId)
            put("method", "tools/list")
            put("params", JSONObject())
        }
        val body = RequestBody.create("application/json".toMediaTypeOrNull(), rpc.toString())

        // 2) Send POST and consume its body as SSE
        val req = Request.Builder()
            .url(mcpUrl)
            .post(body)
            // indicate we expect an event stream in response
            .header("Accept", "text/event-stream")
            .build()

        client.newCall(req).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e("MCPService", "RPC POST failed: ${e.message}")
            }

            override fun onResponse(call: Call, response: Response) {
                if (!response.isSuccessful) {
                    Log.e("MCPService", "RPC POST error: ${response.code}")
                    response.close()
                    return
                }
                Log.d("MCPService", "RPC POST succeeded, streaming SSE for id=$requestId")

                // 3) Read the very POST response as an SSE stream
                executor.execute {
                    BufferedReader(InputStreamReader(response.body!!.byteStream())).use { reader ->
                        var eventType: String? = null
                        val dataBuf = StringBuilder()
                        var line: String?

                        try {
                            while (reader.readLine().also { line = it } != null) {
                                val l = line!!.trim()
                                when {
                                    l.startsWith("event:") -> {
                                        eventType = l.removePrefix("event:").trim()
                                    }
                                    l.startsWith("data:") -> {
                                        dataBuf.append(l.removePrefix("data:").trim())
                                    }
                                    l.isEmpty() -> {
                                        val payload = dataBuf.toString()
                                        if (payload.isNotBlank()) {
                                            handleSse(eventType, payload)
                                        }
                                        eventType = null
                                        dataBuf.setLength(0)
                                    }
                                }
                            }
                        } catch (e: Exception) {
                            Log.e("MCPService", "Error reading SSE: ${e.message}")
                        } finally {
                            response.close()
                        }
                    }
                }
            }
        })
    }

    private fun handleSse(event: String?, data: String) {
        // Only process the JSON-RPC response that matches our ID
        try {
            val js = JSONObject(data)
            if (js.optString("id") == requestId) {
                Log.i("MCPService", "✅ Received matching SSE: $data")
                // TODO: Do something with your result
            } else {
                Log.d("MCPService", "Ignored SSE for id=${js.optString("id")}")
            }
        } catch (e: Exception) {
            Log.w("MCPService", "Non‑JSON SSE payload: $data")
        }
    }

    override fun onDestroy() {
        executor.shutdownNow()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
