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
        .readTimeout(0, TimeUnit.MILLISECONDS) // keep-alive for SSE
        .build()

    private val executor = Executors.newSingleThreadExecutor()
    private val mcpUrl = "http://10.0.2.2:8000/mcp/"

    // Track SSE-level last event ID
    @Volatile private var lastEventId: String? = null
    private var rpcRequestId = ""

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        doRpcAndListen()
        return START_STICKY
    }

    private fun doRpcAndListen() {
        rpcRequestId = UUID.randomUUID().toString()

        // Build JSON-RPC POST
        val rpc = JSONObject().apply {
            put("jsonrpc", "2.0")
            put("id", rpcRequestId)
            put("method", "tools/list")
            put("params", JSONObject())
        }
        val body = RequestBody.create("application/json".toMediaTypeOrNull(), rpc.toString())

        client.newCall(Request.Builder().url(mcpUrl).post(body).build())
            .enqueue(object : Callback {
                override fun onFailure(call: Call, e: IOException) {
                    Log.e("MCPService", "RPC failed: ${e.message}")
                }
                override fun onResponse(call: Call, resp: Response) {
                    resp.close()
                    Log.d("MCPService", "RPC sent id=$rpcRequestId, now connecting SSE…")
                    // immediately open fresh SSE
                    listenSse()
                }
            })
    }

    private fun listenSse() {
        val reqBuilder = Request.Builder()
            .url(mcpUrl)
            .get()
            // if we've seen an SSE id, ask server to start *after* it
            .apply { lastEventId?.let { header("Last-Event-ID", it) } }

        executor.execute {
            client.newCall(reqBuilder.build()).execute().use { resp ->
                if (!resp.isSuccessful) {
                    Log.e("MCPService", "SSE connect error ${resp.code}")
                    return@use
                }
                val reader = BufferedReader(InputStreamReader(resp.body!!.byteStream()))
                var sseId: String? = null
                var eventType: String? = null
                val dataBuf = StringBuilder()

                reader.forEachLine { raw ->
                    val line = raw.trim()
                    when {
                        line.startsWith("id:") -> {
                            sseId = line.removePrefix("id:").trim()
                        }
                        line.startsWith("event:") -> {
                            eventType = line.removePrefix("event:").trim()
                        }
                        line.startsWith("data:") -> {
                            dataBuf.append(line.removePrefix("data:").trim())
                        }
                        line.isEmpty() -> {
                            // end of one SSE message
                            lastEventId = sseId
                            sseId = null

                            val payload = dataBuf.toString().takeIf { it.isNotBlank() }
                            if (payload != null) {
                                processSse(eventType, payload)
                            }
                            // reset for next
                            dataBuf.setLength(0)
                            eventType = null
                        }
                    }
                }
            }
        }
    }

    private fun processSse(event: String?, data: String) {
        // only JSON-RPC results carry your rpcRequestId inside the JSON
        try {
            val js = JSONObject(data)
            if (js.optString("id") == rpcRequestId) {
                Log.i("MCPService", "✅ Got matching RPC result: $data")
                // …handle result…
                //—and stop / restart if you need to send another
            } else {
                Log.d("MCPService", "Ignored other SSE payload: $data")
            }
        } catch (e: Exception) {
            Log.w("MCPService", "Non‑JSON SSE data: $data")
        }
    }

    override fun onDestroy() {
        executor.shutdownNow()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
