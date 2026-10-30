import java.util.Properties

plugins {
    id("com.android.application")
    id("com.chaquo.python")
    id("org.jetbrains.kotlin.android")
}

val generatedPython = layout.buildDirectory.dir("generated/python")
val generatedWeb = layout.buildDirectory.dir("generated/web")
val signingPropertiesFile = rootProject.file("signing.properties")
val signingProperties = Properties().apply {
    if (signingPropertiesFile.exists()) signingPropertiesFile.inputStream().use { load(it) }
}

tasks.register<Sync>("preparePythonSources") {
    from(rootProject.file("../mfnb")) {
        include("**/*.py")
        include("motion/data/**")
    }
    into(generatedPython.map { it.dir("mfnb") })
}

tasks.register<Sync>("prepareWebAssets") {
    from(rootProject.file("../mfnb/web"))
    into(generatedWeb.map { it.dir("web") })
}

android {
    namespace = "org.motorfacialnback.app"
    compileSdk = 35

    kotlinOptions {
        jvmTarget = "1.8"
    }

    defaultConfig {
        applicationId = "org.motorfacialnback.app"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"
        ndk {
            abiFilters += listOf("arm64-v8a", "x86_64")
        }
    }

    sourceSets.getByName("main").assets.srcDir(generatedWeb)

    buildTypes {
        release {
            isMinifyEnabled = false
            val keystore = signingProperties.getProperty("storeFile")
            val keyAlias = signingProperties.getProperty("keyAlias")
            val storePassword = signingProperties.getProperty("storePassword")
            val keyPassword = signingProperties.getProperty("keyPassword")
            if (keystore != null && keyAlias != null && storePassword != null && keyPassword != null) {
                signingConfig = signingConfigs.create("localRelease") {
                    storeFile = file(keystore)
                    this.keyAlias = keyAlias
                    this.storePassword = storePassword
                    this.keyPassword = keyPassword
                }
            }
        }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
}

chaquopy {
    defaultConfig {
        version = "3.12"
        pip {
            install("fastapi==0.99.1")
            install("uvicorn==0.34.0")
            install("pydantic==1.10.26")
            install("numpy==1.26.2")
        }
    }
    sourceSets {
        getByName("main").srcDir(generatedPython)
    }
}

tasks.named("preBuild").configure {
    dependsOn("preparePythonSources", "prepareWebAssets")
}

tasks.configureEach {
    if (name != "preparePythonSources" && name.endsWith("PythonSources")) {
        dependsOn("preparePythonSources")
    }
    if (name != "prepareWebAssets" && name.endsWith("Assets")) {
        dependsOn("prepareWebAssets")
    }
}
