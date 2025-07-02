import okhttp3.*
import org.json.JSONObject
import java.io.IOException

object MCPClient {
    private val client = OkHttpClient()
    private var requestId = 1
    private const val MCP_URL = "http://10.0.2.2:8000/MCP" // Use your real IP for physical device

    fun initialize() {
        val json = JSONObject().apply {
            put("jsonrpc", "2.0")
            put("id", requestId++)
            put("method", "initialize")
            put("params", JSONObject().apply {
                put("capabilities", listOf("tools/call"))
                put("transport", "http")
            })
        }
        post(json)
    }

    fun callTool(toolName: String, args: JSONObject) {
        val json = JSONObject().apply {
            put("jsonrpc", "2.0")
            put("id", requestId++)
            put("method", "tools/call")
            put("params", JSONObject().apply {
                put("name", toolName)
                put("arguments", args)
            })
        }
        post(json)
    }

    private fun post(json: JSONObject) {
        val body = RequestBody.create("application/json".toMediaTypeOrNull(), json.toString())
        val request = Request.Builder()
            .url(MCP_URL)
            .post(body)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                println("Failed: ${e.message}")
            }

            override fun onResponse(call: Call, response: Response) {
                response.body?.string()?.let {
                    println("Response: $it")
                }
            }
        })
    }
}



class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Initialize MCP connection
        MCPClient.initialize()

        // Call a tool after short delay
        Handler(Looper.getMainLooper()).postDelayed({
            val args = JSONObject().apply {
                put("location", "New York")
            }
            MCPClient.callTool("weather", args)
        }, 2000)
    }
}
