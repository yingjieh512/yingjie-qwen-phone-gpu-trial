# AWS Device Farm

AWS Device Farm is planned for hardware validation and repeatable benchmark runs on real Android phones. Phase 4A enables the first manual Remote Access smoke test with a minimal probe APK. It does not start an automated run and does not make performance claims.

## First Remote Access Smoke Test

Use Remote Access for manual app and hardware smoke validation only. Automated Device Farm runs should come later once an instrumentation APK or test runner exists.

1. Build the APK locally:

   ```bash
   cd android/probe-app
   ./gradlew assembleDebug
   ```

   On Windows:

   ```powershell
   cd android\probe-app
   .\gradlew.bat assembleDebug
   ```

2. Find the APK path:

   ```bash
   python scripts/android/find_probe_apk.py
   ```

3. Open the AWS Device Farm console.
4. Choose Remote access.
5. Select an Android Samsung device if available, ideally matching the intended Snapdragon-class target as closely as the device pool allows.
6. Start the Remote Access session.
7. Install or upload the debug APK.
8. Launch `QPNPU Probe`.
9. Tap `Run Probe`.
10. Verify:

    - The UI shows JSON.
    - Logcat contains `QPNPU_PROBE_JSON_BEGIN` and `QPNPU_PROBE_JSON_END`.
    - The app does not crash.
    - Device details in AWS match the expected target class as closely as available.

11. Stop the session.
12. Retrieve logs and video from the session if available.
13. Save any copied probe JSON into:

    ```text
    benchmarks/results/aws_remote_probe_<date>.json
    ```

## What To Record

- AWS device name and model.
- Android version.
- Session ARN.
- Whether the APK installed.
- Whether the probe ran.
- Whether QNN hints were found.
- Whether Vulkan hints were found.
- Whether thermal/sysfs paths were readable.
- Screenshots, if useful.
- Logs and artifacts, especially logcat around the JSON markers.

## Safety Notes

- Remote Access is for manual smoke validation.
- Do not enter sensitive information in remote sessions.
- Do not run Qwen inference or benchmarks in Phase 4A.
- Do not interpret QNN, HTP, Hexagon, Vulkan, or NNAPI string hints as proof of usable accelerator execution.
- Do not claim performance from this app.

## Later Automated Runs

Expected later usage:

- List available Samsung Android devices.
- Create or reuse a Device Farm project.
- Upload probe or benchmark APK artifacts.
- Schedule runs with explicit user-provided AWS credentials.
- Pull result artifacts for schema validation and benchmark analysis.

No AWS credentials are included in this repository, and no Device Farm run is scheduled by Phase 4A tooling.