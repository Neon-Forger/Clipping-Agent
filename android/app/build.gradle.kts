plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val ver = (System.getenv("APP_VERSION_CODE") ?: "1").toInt()

android {
    namespace = "com.neonforger.clipcartel"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.neonforger.clipcartel"
        minSdk = 26
        targetSdk = 34
        versionCode = ver
        versionName = "1.0.$ver"
    }

    signingConfigs {
        create("release") {
            val ks = System.getenv("KEYSTORE_FILE")
            if (ks != null && file(ks).exists()) {
                storeFile = file(ks)
                storePassword = System.getenv("KEYSTORE_PASSWORD")
                keyAlias = System.getenv("KEY_ALIAS")
                keyPassword = System.getenv("KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            val ks = System.getenv("KEYSTORE_FILE")
            signingConfig = if (ks != null && file(ks).exists()) signingConfigs.getByName("release") else signingConfigs.getByName("debug")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildFeatures {
        buildConfig = true
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.work:work-runtime-ktx:2.9.1")
    implementation("androidx.webkit:webkit:1.11.0")
}
