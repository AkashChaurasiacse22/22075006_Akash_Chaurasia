package com.example.test1

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.sse.EventSource
import okhttp3.sse.EventSourceListener
import okhttp3.sse.EventSources
import org.json.JSONObject
import java.io.IOException
import java.util.*
import java.util.concurrent.TimeUnit

class MCPService : Service() {

  private val client = OkHttpClient.Builder()
    .connectTimeout(5, TimeUnit.SECONDS)
    .readTimeout(0, TimeUnit.MILLISECONDS) // keep-alive for SSE
    .build()

  private val mcpUrl = "http://10.0.2.2:8000/mcp/"
  private var eventSource: EventSource? = null
  private var rpcRequestId = ""

  override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
    sendRpcThenOpenSse()
    return START_STICKY
  }

  private fun sendRpcThenOpenSse() {
    // 1) Generate a unique JSON-RPC id
    rpcRequestId = UUID.randomUUID().toString()

    // 2) Build and send JSON-RPC POST
    val rpc = JSONObject().apply {
      put("jsonrpc", "2.0")
      put("id", rpcRequestId)
      put("method", "tools/list")
      put("params", JSONObject())
    }
    val body = RequestBody.create("application/json".toMediaTypeOrNull(), rpc.toString())
    client.newCall(Request.Builder()
        .url(mcpUrl)
        .post(body)
        .build()
    ).enqueue(object : okhttp3.Callback {
      override fun onFailure(call: okhttp3.Call, e: IOException) {
        Log.e("MCPService", "RPC POST failed: ${e.message}")
      }
      override fun onResponse(call: okhttp3.Call, response: okhttp3.Response) {
        response.close()
        Log.d("MCPService", "RPC sent, id=$rpcRequestId → opening SSE…")
        startSseListener()
      }
    })
  }

  private fun startSseListener() {
    // If an existing EventSource is open, close it
    eventSource?.cancel()

    val request = Request.Builder()
      .url(mcpUrl)
      .header("Accept", "text/event-stream")
      .build()

    // 3) Create a proper EventSource
    eventSource = EventSources.createFactory(client)
      .newEventSource(request, object : EventSourceListener() {
        override fun onOpen(source: EventSource, response: okhttp3.Response) {
          Log.d("MCPService", "SSE connection opened")
        }

        override fun onEvent(
          source: EventSource,
          id: String?,
          type: String?,
          data: String
        ) {
          // Called **only** for each new incoming SSE event
          Log.v("MCPService", "SSE event id=$id type=$type data=$data")

          // Try to parse JSON-RPC response
          try {
            val json = JSONObject(data)
            if (json.optString("id") == rpcRequestId) {
              Log.i("MCPService", "✅ Matched RPC result: $data")
              // TODO: Handle your result here
              // If you only want one response, cancel the stream:
              source.cancel()
            } else {
              Log.d("MCPService", "Ignored SSE (wrong RPC id)")
            }
          } catch (e: Exception) {
            Log.w("MCPService", "Non‑JSON SSE payload: $data")
          }
        }

        override fun onClosed(source: EventSource) {
          Log.d("MCPService", "SSE connection closed")
        }

        override fun onFailure(
          source: EventSource,
          t: Throwable?,
          response: okhttp3.Response?
        ) {
          Log.e("MCPService", "SSE failure: ${t?.message}")
          source.cancel()
        }
      })
  }

  override fun onDestroy() {
    eventSource?.cancel()
    super.onDestroy()
  }

  override fun onBind(intent: Intent?): IBinder? = null
}
