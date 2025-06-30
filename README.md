// -------------------------------------------
// FILE 1: llm_server/llm_server.py
// -------------------------------------------

from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    query = data.get("query", "").lower()

    if "youtube" in query:
        return jsonify({"tool": "launch_app", "parameters": {"app": "com.google.android.youtube"}})
    elif "screen size" in query:
        return jsonify({"tool": "get_screen_size", "parameters": {}})
    else:
        return jsonify({"tool": "echo", "parameters": {"message": "Unknown command."}})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)


// -------------------------------------------
// FILE 2: AndroidManifest.xml
// -------------------------------------------

<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.llmautomation">

    <uses-permission android:name="android.permission.INTERNET"/>

    <application
        android:allowBackup="true"
        android:label="LLM Automation"
        android:supportsRtl="true"
        android:theme="@style/Theme.AppCompat.Light.NoActionBar">
        <activity android:name=".MainActivity">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>

</manifest>


// -------------------------------------------
// FILE 3: res/layout/activity_main.xml
// -------------------------------------------

<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="16dp">

    <EditText
        android:id="@+id/queryInput"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:hint="Enter your command"/>

    <Button
        android:id="@+id/submitButton"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Send Query"/>

    <TextView
        android:id="@+id/resultText"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:paddingTop="20dp"
        android:textSize="16sp"/>

</LinearLayout>


// -------------------------------------------
// FILE 4: MainActivity.kt
// -------------------------------------------

package com.example.llmautomation

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import okhttp3.*
import org.json.JSONObject
import java.io.IOException

class MainActivity : AppCompatActivity() {

    private val llmUrl = "http://192.168.1.100:5000/generate" // Replace with your IP
    private val mcpUrl = "http://192.168.1.100:3000" // Replace with your IP

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val queryInput = findViewById<EditText>(R.id.queryInput)
        val submitButton = findViewById<Button>(R.id.submitButton)
        val resultText = findViewById<TextView>(R.id.resultText)

        submitButton.setOnClickListener {
            val query = queryInput.text.toString()
            sendQueryToLLM(query) { tool, params ->
                callMCP(tool, params) { response ->
                    runOnUiThread {
                        resultText.text = response
                    }
                }
            }
        }
    }

    private fun sendQueryToLLM(query: String, callback: (String, JSONObject) -> Unit) {
        val client = OkHttpClient()
        val json = JSONObject().put("query", query)
        val body = RequestBody.create(MediaType.get("application/json"), json.toString())
        val request = Request.Builder().url(llmUrl).post(body).build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {}
            override fun onResponse(call: Call, response: Response) {
                val jsonResp = JSONObject(response.body()?.string() ?: "")
                val tool = jsonResp.getString("tool")
                val params = jsonResp.getJSONObject("parameters")
                callback(tool, params)
            }
        })
    }

    private fun callMCP(tool: String, params: JSONObject, callback: (String) -> Unit) {
        val client = OkHttpClient()
        val body = RequestBody.create(MediaType.get("application/json"), params.toString())
        val request = Request.Builder()
            .url("$mcpUrl/tools/$tool/run")
            .post(body)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                callback("Failed to call MCP: ${e.message}")
            }
            override fun onResponse(call: Call, response: Response) {
                callback(response.body()?.string() ?: "No response")
            }
        })
    }
}
