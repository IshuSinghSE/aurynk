package com.devindeed.aurelay.desktop

import androidx.compose.desktop.ui.tooling.preview.Preview
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application

@Composable
@Preview
fun App() {
    val teal = Color(0xFF03DAC5)
    val pink = Color(0xFFFA5995)

    val colors = darkColorScheme(
        primary = teal,
        secondary = pink,
        onPrimary = Color.Black,
        onSecondary = Color.White,
        background = Color(0xFF121212),
        surface = Color(0xFF1E1E1E)
    )

    MaterialTheme(colorScheme = colors) {
        Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
            MainScreen()
        }
    }
}

@Composable
fun MainScreen() {
    var targetIp by remember { mutableStateOf("192.168.1.100") }
    var isStreaming by remember { mutableStateOf(false) }
    var statusText by remember { mutableStateOf("Idle") }

    Column(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "Desktop Server",
            style = MaterialTheme.typography.headlineLarge,
            color = MaterialTheme.colorScheme.primary
        )

        Spacer(modifier = Modifier.height(32.dp))

        OutlinedTextField(
            value = targetIp,
            onValueChange = { targetIp = it },
            label = { Text("Target IP") },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isStreaming
        )

        Spacer(modifier = Modifier.height(24.dp))

        Button(
            onClick = {
                if (isStreaming) {
                    AudioEngine.stopStream()
                    isStreaming = false
                    statusText = "Idle"
                } else {
                    // Launch in a coroutine if startStream was blocking, but it's native and supposedly non-blocking (returns int).
                    // However, if it takes time to init, it might block UI.
                    // For MVP we assume it's fast.
                    val result = AudioEngine.startStream(targetIp)
                    if (result == 0) {
                        isStreaming = true
                        statusText = "Streaming to $targetIp..."
                    } else {
                        statusText = "Error starting stream: $result"
                    }
                }
            },
            modifier = Modifier.size(width = 200.dp, height = 60.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = if (isStreaming) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.primary
            )
        ) {
            Text(
                text = if (isStreaming) "STOP" else "START",
                style = MaterialTheme.typography.titleMedium
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "Status: $statusText",
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onBackground
        )
    }
}

fun main() = application {
    Window(onCloseRequest = ::exitApplication, title = "Aurelay Sender") {
        App()
    }
}
