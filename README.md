package com.example.test1

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.sse.EventSource
import okhttp3.sse.EventSourceListener
import okhttp3.sse.EventSources
import org.json.JSONObject
import java.util.*

class MCPService : Service() {

    private val TAG = "MCPService"
    private val client = OkHttpClient.Builder().build()
    private val mcpUrl = "http://10.0.2.2:8000/mcp/"

    private var currentRequestId = ""
    private var eventSource: EventSource? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Only start SSE once
        if (eventSource == null) {
            startSSEListener()
        }

        // You can trigger RPC here or from UI
        triggerToolsListRpc()

        return START_STICKY
    }

    private fun triggerToolsListRpc() {
        currentRequestId = UUID.randomUUID().toString()

        val json = JSONObject().apply {
            put("jsonrpc", "2.0")
            put("id", currentRequestId)
            put("method", "tools/list")
            put("params", JSONObject())
        }

        val body = json.toString().toRequestBody("application/json".toMediaTypeOrNull())

        val request = Request.Builder()
            .url(mcpUrl)
            .post(body)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: java.io.IOException) {
                Log.e(TAG, "❌ JSON-RPC POST failed: ${e.message}")
            }

            override fun onResponse(call: Call, response: Response) {
                Log.d(TAG, "✅ RPC sent with id=$currentRequestId, HTTP ${response.code}")
                response.close()
            }
        })
    }

    private fun startSSEListener() {
        val request = Request.Builder()
            .url(mcpUrl)
            .addHeader("Accept", "text/event-stream")
            .build()

        eventSource = EventSources.createFactory(client)
            .newEventSource(request, object : EventSourceListener() {

                override fun onOpen(eventSource: EventSource, response: Response) {
                    Log.d(TAG, "🔗 SSE connection established")
                }

                override fun onEvent(
                    eventSource: EventSource,
                    id: String?,
                    type: String?,
                    data: String
                ) {
                    Log.d(TAG, "📥 SSE event: $data")
                    try {
                        val json = JSONObject(data)
                        val responseId = json.optString("id", "")
                        if (responseId == currentRequestId) {
                            Log.i(TAG, "✅ Received expected response for ID=$responseId")
                            // Process your successful result here
                        } else {
                            Log.d(TAG, "ℹ️ Ignored unrelated SSE message with ID=$responseId")
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "❌ Failed to parse SSE data: ${e.message}")
                    }
                }

                override fun onFailure(eventSource: EventSource, t: Throwable?, response: Response?) {
                    Log.e(TAG, "❌ SSE connection failed: ${t?.message}")
                }

                override fun onClosed(eventSource: EventSource) {
                    Log.d(TAG, "🔒 SSE connection closed")
                }
            })
    }

    override fun onDestroy() {
        eventSource?.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
