plugins {
    id 'com.android.application'
}

android {
    namespace '{{PACKAGE}}'
    compileSdk 34

    defaultConfig {
        applicationId '{{PACKAGE}}'
        minSdk 24
        targetSdk 34
        versionCode {{VERSION_CODE}}
        versionName '{{VERSION_NAME}}'
    }

    buildTypes {
        release {
            minifyEnabled false
        }
    }

    compileOptions {
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }
}
