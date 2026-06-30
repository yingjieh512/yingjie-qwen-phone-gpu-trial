# QPNPU Probe App

Minimal Java-only Android app for the first AWS Device Farm Remote Access smoke test.

The package name is `com.qpnpu.trial`. The app displays a basic best-effort hardware probe JSON report, logs the same JSON to logcat between `QPNPU_PROBE_JSON_BEGIN` and `QPNPU_PROBE_JSON_END`, and tries to save it to `getExternalFilesDir(null)/probe_result.json`.

This is not a Qwen inference app, does not use QNN/NPU execution, and does not make performance claims.

## Build

With Android Studio, open this directory and build the `app` module.

With an installed Gradle and Android SDK:

```bash
gradle assembleDebug
```

The included `gradlew` and `gradlew.bat` scripts delegate to an installed `gradle` command if one exists. They do not vendor a Gradle wrapper jar.

Expected APK:

```text
app/build/outputs/apk/debug/app-debug.apk
```