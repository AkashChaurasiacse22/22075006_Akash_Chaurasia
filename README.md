<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:orientation="vertical"
    android:padding="24dp"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <Button
        android:id="@+id/launchButton"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Launch YouTube App" />

    <Button
        android:id="@+id/screenButton"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginTop="16dp"
        android:text="Get Screen Size" />

    <TextView
        android:id="@+id/resultView"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Result will appear here"
        android:paddingTop="20dp"
        android:textSize="16sp" />
</LinearLayout>


<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.mcpdemo">

    <uses-permission android:name="android.permission.INTERNET"/>

    <application
        android:allowBackup="true"
        android:label="MCP Demo"
        android:supportsRtl="true"
        android:theme="@style/Theme.AppCompat.Light.DarkActionBar">
        <activity android:name=".MainActivity">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
    </application>
</manifest>

package com.example.mcpdemo

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import okhttp3.*
import org.json.JSONObject
import java.io.IOException
import okhttp3.MediaType.Companion.toMediaTypeOrNull

class MainActivity : AppCompatActivity() {

    private val client = OkHttpClient()

    // Replace with your laptop IP (where MCP is running)
    private val mcpBaseUrl = "http://192.168.1.100:3000"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val launchButton = findViewById<Button>(R.id.launchButton)
        val screenButton = findViewById<Button>(R.id.screenButton)
        val resultView = findViewById<TextView>(R.id.resultView)

        launchButton.setOnClickListener {
            callMcp("launch_app", JSONObject().put("app", "com.google.android.youtube")) {
                runOnUiThread { resultView.text = it }
            }
        }

        screenButton.setOnClickListener {
            callMcp("get_screen_size", JSONObject()) {
                runOnUiThread { resultView.text = it }
            }
        }
    }

    private fun callMcp(tool: String, params: JSONObject, callback: (String) -> Unit) {
        val body = RequestBody.create("application/json".toMediaTypeOrNull(), params.toString())
        val request = Request.Builder()
            .url("$mcpBaseUrl/tools/$tool/run")
            .post(body)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                callback("Error: ${e.message}")
            }

            override fun onResponse(call: Call, response: Response) {
                callback(response.body?.string() ?: "No response")
            }
        })
    }
}



dependencies {
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'com.squareup.okhttp3:okhttp:4.9.3'
}
