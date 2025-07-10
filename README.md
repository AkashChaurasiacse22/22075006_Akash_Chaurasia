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
    private val mcpUrl = "http://10.0.2.2:8000/mcp/"
    private val client = OkHttpClient.Builder().build()
    private var eventSource: EventSource? = null
    private val pendingIds = Collections.synchronizedSet(mutableSetOf<String>())

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        connectSSE()
        // Example POST; call this anytime you need a request
        sendJsonRpc("tools/list", JSONObject())
        return START_STICKY
    }

    /** 1️⃣ Open SSE stream once and keep alive */
    private fun connectSSE() {
        if (eventSource != null) return

        val request = Request.Builder()
            .url(mcpUrl)
            .header("Accept", "text/event-stream")
            .build()

        eventSource = EventSources.createFactory(client).newEventSource(request, object : EventSourceListener() {
            override fun onOpen(es: EventSource, response: Response) {
                Log.d(TAG, "SSE connected")
            }
            override fun onEvent(es: EventSource, id: String?, type: String?, data: String) {
                Log.d(TAG, "SSE got data: $data")
                try {
                    val json = JSONObject(data)
                    val respId = json.optString("id")
                    if (pendingIds.contains(respId)) {
                        Log.i(TAG, "✅ Matched id=$respId: $data")
                        pendingIds.remove(respId)
                        // TODO: process your result
                    } else {
                        Log.d(TAG, "Ignored id=$respId")
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Invalid SSE data", e)
                }
            }
            override fun onFailure(es: EventSource, t: Throwable?, resp: Response?) {
                Log.e(TAG, "SSE failed", t)
                eventSource = null
                // optionally reconnect
            }
            override fun onClosed(es: EventSource) {
                Log.d(TAG, "SSE closed")
                eventSource = null
            }
        })
    }

    /** 2️⃣ Send JSON-RPC via POST; response will come over SSE */
    private fun sendJsonRpc(method: String, params: JSONObject) {
        val id = UUID.randomUUID().toString()
        pendingIds.add(id)

        val json = JSONObject().apply {
            put("jsonrpc", "2.0")
            put("id", id)
            put("method", method)
            put("params", params)
        }
        val body = json.toString().toRequestBody("application/json".toMediaTypeOrNull())
        val request = Request.Builder()
            .url(mcpUrl)
            .post(body)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(c: Call, e: java.io.IOException) {
                pendingIds.remove(id)
                Log.e(TAG, "POST failed for id=$id", e)
            }
            override fun onResponse(c: Call, resp: Response) {
                Log.d(TAG, "POST sent id=$id, HTTP ${resp.code}")
                resp.close()
            }
        })
    }

    override fun onDestroy() {
        eventSource?.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
