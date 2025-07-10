package com.example.test1

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaTypeOrNull
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
    .readTimeout(0, TimeUnit.MILLISECONDS)
    .build()

  private val mcpUrl = "http://10.0.2.2:8000/mcp/"
  private var rpcRequestId = ""
  private var eventSource: EventSource? = null

  override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
    sendRpcAndPrimeSse()
    return START_STICKY
  }

  private fun sendRpcAndPrimeSse() {
    rpcRequestId = UUID.randomUUID().toString()
    val rpcJson = JSONObject().apply {
      put("jsonrpc", "2.0")
      put("id", rpcRequestId)
      put("method", "tools/list")
      put("params", JSONObject())
    }
    val body = RequestBody.create("application/json".toMediaTypeOrNull(), rpcJson.toString())

    // 1) send the JSON‑RPC POST
    client.newCall(Request.Builder()
        .url(mcpUrl)
        .post(body)
        .build()
    ).enqueue(object : Callback {
      override fun onFailure(call: Call, e: IOException) {
        Log.e("MCPService", "RPC POST failed: ${e.message}")
      }
      override fun onResponse(call: Call, resp: Response) {
        resp.close()
        Log.d("MCPService", "RPC sent (id=$rpcRequestId). Priming SSE…")

        // 2) fire a plain GET to clear any old SSE backlog
        client.newCall(Request.Builder()
            .url(mcpUrl)
            .get()
            .build()
        ).enqueue(object : Callback {
          override fun onFailure(call: Call, e: IOException) {
            Log.e("MCPService", "Prime GET failed: ${e.message}")
          }
          override fun onResponse(call: Call, primeResp: Response) {
            primeResp.close()
            Log.d("MCPService", "Prime GET done. Now opening SSE.")
            startSseListener()
          }
        })
      }
    })
  }

  private fun startSseListener() {
    // close any old stream
    eventSource?.cancel()

    val request = Request.Builder()
      .url(mcpUrl)
      .header("Accept", "text/event-stream")
      .build()

    eventSource = EventSources.createFactory(client)
      .newEventSource(request, object : EventSourceListener() {
        override fun onOpen(source: EventSource, response: Response) {
          Log.d("MCPService", "SSE opened")
        }
        override fun onEvent(source: EventSource, id: String?, type: String?, data: String) {
          Log.v("MCPService", "SSE → id=$id type=$type data=$data")
          try {
            val js = JSONObject(data)
            if (js.optString("id") == rpcRequestId) {
              Log.i("MCPService", "✅ Got matching result: $data")
              source.cancel() // stop further reading
            } else {
              Log.d("MCPService", "Ignored event for id=${js.optString("id")}")
            }
          } catch (e: Exception) {
            Log.w("MCPService", "Non‑JSON SSE payload: $data")
          }
        }
        override fun onClosed(source: EventSource) {
          Log.d("MCPService", "SSE closed")
        }
        override fun onFailure(source: EventSource, t: Throwable?, response: Response?) {
          Log.e("MCPService", "SSE failed: ${t?.message}")
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
