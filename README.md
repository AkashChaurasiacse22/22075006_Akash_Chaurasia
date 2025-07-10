import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.os.Handler
import android.os.Looper
import android.util.Log
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.sse.EventSource
import okhttp3.sse.EventSourceListener
import okhttp3.sse.EventSources
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

class MCPService : Service() {
    private val TAG = "MCPService"
    private val mcpUrl = "http://10.0.2.2:8000/mcp/"
    private lateinit var client: OkHttpClient
    private var eventSource: EventSource? = null
    private var idCounter = 0
    private val pendingResponses = mutableMapOf<String, (JSONObject) -> Unit>()

    override fun onCreate() {
        super.onCreate()
        // Configure OkHttp with infinite read timeout to keep SSE alive
        client = OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(0, TimeUnit.MILLISECONDS)    // infinite
            .retryOnConnectionFailure(true)
            .build()
        connectSSE()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Service will continue running until explicitly stopped
        return START_STICKY
    }

    override fun onDestroy() {
        // Clean up the SSE connection
        eventSource?.cancel()
        eventSource = null
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? {
        // Not a bound service
        return null
    }

    /** Establish the SSE (GET) connection if not already connected. */
    private fun connectSSE() {
        if (eventSource != null) {
            Log.d(TAG, "SSE already connected")
            return
        }
        val request = Request.Builder()
            .url(mcpUrl)
            .header("Accept", "text/event-stream")  // Important SSE header:contentReference[oaicite:4]{index=4}
            .build()

        val listener = object : EventSourceListener() {
            override fun onOpen(source: EventSource, response: Response) {
                super.onOpen(source, response)
                Log.d(TAG, "SSE connection opened")
            }
            override fun onEvent(source: EventSource, id: String?, type: String?, data: String) {
                super.onEvent(source, id, type, data)
                Log.d(TAG, "SSE event received: $data")
                try {
                    val json = JSONObject(data)
                    val respId = json.optString("id", "")
                    // Match the response by ID to the original request
                    if (pendingResponses.containsKey(respId)) {
                        pendingResponses[respId]?.invoke(json)
                        pendingResponses.remove(respId)
                    } else {
                        Log.w(TAG, "No pending request for id=$respId")
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to parse SSE JSON", e)
                }
            }
            override fun onClosed(source: EventSource) {
                super.onClosed(source)
                Log.d(TAG, "SSE connection closed")
                eventSource = null
                reconnectSSE()
            }
            override fun onFailure(source: EventSource, t: Throwable?, response: Response?) {
                super.onFailure(source, t, response)
                Log.e(TAG, "SSE connection failed", t)
                eventSource = null
                reconnectSSE()
            }
        }

        // Open the SSE connection (asynchronously)
        eventSource = EventSources.createFactory(client).newEventSource(request, listener)
    }

    /** Retry connecting after delay (simple back-off). */
    private fun reconnectSSE() {
        Handler(Looper.getMainLooper()).postDelayed({
            Log.d(TAG, "Reconnecting SSE...")
            connectSSE()
        }, 5000)
    }

    /**
     * Send a JSON-RPC 2.0 request via POST.
     * The JSON will include "jsonrpc":"2.0", "method", "params", and a unique "id".
     * The server will respond over the SSE stream with the same "id" to match the request:contentReference[oaicite:5]{index=5}.
     */
    fun sendJsonRpc(method: String, params: JSONObject = JSONObject(), callback: (JSONObject) -> Unit) {
        val id = (++idCounter).toString()
        val json = JSONObject().apply {
            put("jsonrpc", "2.0")
            put("method", method)
            put("params", params)
            put("id", id)
        }
        // Store callback to handle response when SSE arrives
        pendingResponses[id] = callback

        // Build request body as JSON
        val mediaType = "application/json; charset=utf-8".toMediaType()
        val body = json.toString().toRequestBody(mediaType)

        val request = Request.Builder()
            .url(mcpUrl)
            .post(body)
            .addHeader("Content-Type", "application/json")
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e(TAG, "JSON-RPC request failed", e)
                pendingResponses.remove(id)
            }
            override fun onResponse(call: Call, response: Response) {
                Log.d(TAG, "JSON-RPC HTTP response code: ${response.code}")
                response.close()
            }
        })
    }
}
