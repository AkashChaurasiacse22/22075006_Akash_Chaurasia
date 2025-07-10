package com.example.sseclient

import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import com.example.sseclient.databinding.ActivityMainBinding
import com.launchdarkly.eventsource.EventHandler
import com.launchdarkly.eventsource.EventSource
import com.launchdarkly.eventsource.MessageEvent
import okhttp3.*
import java.net.URI
import java.util.concurrent.TimeUnit

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private val TAG = "SSEClient"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.startStreamBtn.setOnClickListener {
            startStreaming()
        }
    }

    private fun startStreaming() {
        // Simulated: Send POST with JSON
        val json = """
            {
                "user_id": "123",
                "filter": "realtime"
            }
        """.trimIndent()

        val requestBody = RequestBody.create("application/json".toMediaTypeOrNull(), json)
        val client = OkHttpClient()

        val request = Request.Builder()
            .url("https://your-sse-server.com/start-stream") // Replace with actual
            .post(requestBody)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: java.io.IOException) {
                Log.e(TAG, "Failed to start stream: ${e.message}")
            }

            override fun onResponse(call: Call, response: Response) {
                if (response.isSuccessful) {
                    // Here assume the server returns the stream URL as plain text
                    val streamUrl = response.body?.string()?.trim() ?: return
                    connectToSSE(streamUrl)
                } else {
                    Log.e(TAG, "Start stream failed: ${response.code}")
                }
            }
        })
    }

    private fun connectToSSE(url: String) {
        val client = OkHttpClient.Builder()
            .readTimeout(0, TimeUnit.MILLISECONDS)
            .build()

        val handler = object : EventHandler {
            override fun onOpen() {
                runOnUiThread {
                    binding.streamTextView.append("\n[Stream Opened]\n")
                }
            }

            override fun onClosed() {
                runOnUiThread {
                    binding.streamTextView.append("\n[Stream Closed]\n")
                }
            }

            override fun onMessage(event: String?, messageEvent: MessageEvent) {
                runOnUiThread {
                    binding.streamTextView.append("\nMessage: ${messageEvent.data}")
                }
            }

            override fun onComment(comment: String?) {}
            override fun onError(t: Throwable?) {
                Log.e(TAG, "SSE error: ${t?.message}")
            }
        }

        val eventSource = EventSource.Builder(handler, URI.create(url))
            .client(client)
            .build()

        eventSource.start()
    }
}
