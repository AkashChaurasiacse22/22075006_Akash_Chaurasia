package com.example.sseclient

import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import com.example.sseclient.databinding.ActivityMainBinding
import okhttp3.*
import okhttp3.sse.EventSource
import okhttp3.sse.EventSourceListener
import okhttp3.sse.EventSources
import java.util.concurrent.TimeUnit

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val TAG = "SSEClient"

    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.startStreamBtn.setOnClickListener {
            startMCPStream()
        }
    }

    private fun startMCPStream() {
        val jsonBody = """
            {
              "jsonrpc": "2.0",
              "id": "1",
              "method": "test.method",
              "params": {
                "message": "Hello from Android"
              }
            }
        """.trimIndent()

        val request = Request.Builder()
            .url("http://10.0.2.2:8080/mcp/stream") // replace with your server's endpoint
            .post(RequestBody.create("application/json".toMediaTypeOrNull(), jsonBody))
            .addHeader("Accept", "text/event-stream")
            .build()

        val eventListener = object : EventSourceListener() {
            override fun onOpen(eventSource: EventSource, response: Response) {
                Log.d(TAG, "Stream Opened")
                runOnUiThread {
                    binding.streamTextView.append("\n[Stream Opened]\n")
                }
            }

            override fun onEvent(
                eventSource: EventSource,
                id: String?,
                type: String?,
                data: String
            ) {
                Log.d(TAG, "Event Received: $data")
                runOnUiThread {
                    binding.streamTextView.append("\n$data\n")
                }
            }

            override fun onFailure(
                eventSource: EventSource,
                t: Throwable?,
                response: Response?
            ) {
                Log.e(TAG, "Stream Failed: ${t?.message}")
                runOnUiThread {
                    binding.streamTextView.append("\n[Error: ${t?.message}]\n")
                }
            }

            override fun onClosed(eventSource: EventSource) {
                Log.d(TAG, "Stream Closed")
                runOnUiThread {
                    binding.streamTextView.append("\n[Stream Closed]\n")
                }
            }
        }

        EventSources.createFactory(client).newEventSource(request, eventListener)
    }
}
