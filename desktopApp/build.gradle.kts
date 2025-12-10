plugins {
    alias(libs.plugins.kotlinMultiplatform)
    alias(libs.plugins.composeMultiplatform)
}

kotlin {
    jvm {
        withJava()
    }

    sourceSets {
        val jvmMain by getting {
            dependencies {
                implementation(compose.desktop.currentOs)
                implementation(compose.material3)
            }
        }
    }
}

tasks.register<Exec>("cargoBuild") {
    group = "rust"
    description = "Builds the Rust engine"
    workingDir = file("../rust_engine")
    commandLine("cargo", "build", "--release")

    doLast {
        val buildDir = file("../rust_engine/target/release")
        val destDir = file("src/jvmMain/resources")

        // Linux
        val soFile = File(buildDir, "librust_engine.so")
        if (soFile.exists()) {
            copy {
                from(soFile)
                into(destDir)
            }
        }

        // Windows (dll)
        val dllFile = File(buildDir, "rust_engine.dll")
        if (dllFile.exists()) {
             copy {
                from(dllFile)
                into(destDir)
            }
        }
    }
}

// Ensure cargoBuild runs before processResources
tasks.named("processResources") {
    dependsOn("cargoBuild")
}
