package com.devindeed.aurelay.desktop

import java.io.File
import java.nio.file.Files
import java.nio.file.StandardCopyOption

object AudioEngine {
    init {
        try {
            // Try loading from java.library.path first
            System.loadLibrary("rust_engine")
        } catch (e: UnsatisfiedLinkError) {
            // Fallback: Extract from JAR/resources
            try {
                loadLibFromResources("rust_engine")
            } catch (ex: Exception) {
                ex.printStackTrace()
                throw RuntimeException("Failed to load native library rust_engine", ex)
            }
        }
    }

    /**
     * Starts the audio stream to the specified target IP.
     * @param targetIp The IP address of the receiver.
     * @return 0 on success, negative error code on failure.
     */
    external fun startStream(targetIp: String): Int

    /**
     * Stops the current audio stream.
     */
    external fun stopStream()

    private fun loadLibFromResources(libName: String) {
        val os = System.getProperty("os.name").lowercase()
        val ext = if (os.contains("win")) ".dll" else ".so"
        val prefix = if (os.contains("win")) "" else "lib"
        val fileName = "$prefix$libName$ext"

        val stream = AudioEngine::class.java.getResourceAsStream("/$fileName")
            ?: throw RuntimeException("Library $fileName not found in resources")

        val tempFile = File.createTempFile(prefix + libName, ext)
        tempFile.deleteOnExit()

        Files.copy(stream, tempFile.toPath(), StandardCopyOption.REPLACE_EXISTING)
        System.load(tempFile.absolutePath)
    }
}
