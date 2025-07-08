package com.example.test1

import android.app.IntentService
import android.content.Intent
import android.os.Handler
import android.os.Looper
import android.widget.Toast
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import org.json.JSONObject

class GeminiMcpLoopService : IntentService("GeminiMcpLoopService") {

    private val geminiApiKey = "YOUR_GEMINI_API_KEY"
    private val mcpUrl = "http://10.0.2.2:8000/mcp/"
    private val client = OkHttpClient()

    override fun onHandleIntent(intent: Intent?) {
        val initialPrompt = intent?.getStringExtra("prompt") ?: return

        var currentInput = initialPrompt
        var iteration = 0
        var stop = false

        while (!stop && iteration < 10) { // prevent infinite loop
            iteration++

            val geminiResponse = callGemini(currentInput) ?: break
            showToast("Gemini: $geminiResponse")

            // Stop if Gemini says task is completed
            if (geminiResponse.contains("completed", ignoreCase = true)) {
                showToast("Task completed.")
                break
            }

            val mcpResponse = callMcp(geminiResponse) ?: break
            showToast("MCP: $mcpResponse")

            currentInput = mcpResponse // feed MCP response back to Gemini
            Thread.sleep(1500)
        }
    }

    private fun callGemini(prompt: String): String? {
        return try {
            val url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=$geminiApiKey"
            val requestBody = JSONObject().apply {
                put("contents", listOf(JSONObject().apply {
                    put("parts", listOf(JSONObject().apply {
                        put("text", prompt)
                    }))
                }))
            }
            val body = RequestBody.create("application/json".toMediaTypeOrNull(), requestBody.toString())
            val request = Request.Builder().url(url).post(body).build()
            client.newCall(request).execute().use { response ->
                val responseBody = response.body?.string()
                val json = JSONObject(responseBody ?: "")
                json.getJSONArray("candidates")
                    .getJSONObject(0)
                    .getJSONObject("content")
                    .getJSONArray("parts")
                    .getJSONObject(0)
                    .getString("text")
            }
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    private fun callMcp(jsonText: String): String? {
        return try {
            val json = JSONObject(jsonText)
            val body = RequestBody.create("application/json".toMediaTypeOrNull(), json.toString())
            val request = Request.Builder().url(mcpUrl).post(body).build()
            client.newCall(request).execute().use { response ->
                response.body?.string()
            }
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    private fun showToast(text: String) {
        Handler(Looper.getMainLooper()).post {
            Toast.makeText(applicationContext, text.take(500), Toast.LENGTH_LONG).show()
        }
    }
}
