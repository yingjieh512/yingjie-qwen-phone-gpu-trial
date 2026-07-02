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
8. Launch `QPNPU Hardware Probe`.
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

## Phase 5 Native Microbenchmark Smoke Test

After the Phase 5 APK is built and uploaded, use the same Remote Access flow but run both app actions:

1. Launch `QPNPU Hardware Probe`.
2. Tap `Run Probe` to collect hardware characterization JSON.
3. Tap `Native Bench` to run the tiny CPU-only JNI/NDK benchmark fixtures.
4. Confirm the UI updates with standalone native benchmark JSON.
5. Confirm logcat contains:

   ```text
   QPNPU_NATIVE_BENCH_JSON_BEGIN
   QPNPU_NATIVE_BENCH_JSON_END
   ```

6. Download or copy the session logcat when available.
7. Extract the standalone native benchmark payload:

   ```bash
   python scripts/android/extract_probe_json_from_logcat.py \
     --kind native \
     --logcat path/to/devicefarm-logcat.txt \
     --out benchmarks/results/aws_remote_native_microbench_<date>.json
   ```

Record whether each native fixture reported `correctness_passed: true`:

- `fp32_matvec`
- `int4_dequant_matvec`
- `rmsnorm`
- `softmax`
- `rope`

These results only validate APK packaging, JNI, native CPU execution, timing, and JSON extraction. They are not Qwen 9B inference, not QNN/NPU execution, and not a tokens/sec performance claim.
## Phase 6 Characterization Smoke Test

After installing the Phase 6 APK in Remote Access:

1. Launch `QPNPU Hardware Probe`.
2. Tap `Characterize HW`.
3. Verify the UI shows characterization JSON and the app does not crash.
4. Confirm logcat contains:

   ```text
   QPNPU_PHASE6_JSON_BEGIN
   QPNPU_PHASE6_JSON_END
   ```

5. Extract the payload:

   ```bash
   python scripts/android/extract_probe_json_from_logcat.py \
     --kind phase6 \
     --logcat path/to/devicefarm-logcat.txt \
     --out benchmarks/results/aws_remote_phase6_<date>.json
   ```

Record CPU ISA feature agreement, thread scaling, memory probe output, backend library load statuses, and quantization fixture correctness. Do not interpret `dlopen` success as accelerator execution.
## What To Record

- AWS device name and model.
- Android version.
- Session ARN.
- Whether the APK installed.
- Whether the probe ran.
- Whether QNN hints were found.
- Whether Vulkan hints were found.
- Whether thermal/sysfs paths were readable.
- Whether native CPU microbenchmarks ran and passed correctness checks.
- Whether Android toy decode ran and emitted generated token IDs.
- Screenshots, if useful.
- Logs and artifacts, especially logcat around the JSON markers.

## Safety Notes

- Remote Access is for manual smoke validation.
- Do not enter sensitive information in remote sessions.
- Do not run real Qwen inference in Remote Access until a later explicit model phase.
- Treat Phase 5 native microbenchmarks as CPU harness validation only.
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

## Phase 7A Guarded ISA Probe Smoke Test

After installing the Phase 7A APK in Remote Access:

1. Launch `QPNPU Hardware Probe`.
2. Tap `ISA Probe`.
3. Verify the UI shows guarded ISA probe JSON and the app does not crash.
4. Confirm logcat contains:

```text
QPNPU_PHASE7A_JSON_BEGIN
QPNPU_PHASE7A_JSON_END
```

5. Download logcat and extract:

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind phase7a \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_phase7a_<date>.json
```

Record:

- Which features were reported.
- Which probes returned `executed_ok`.
- Whether any probe returned `sigill`.
- Whether any feature was skipped or deferred.
- App stability and Device Farm session status.

These ISA probes validate tiny CPU instruction fixtures only. They are not Qwen inference, not accelerator execution, and not a performance claim.

## Phase 7B Android Toy Decode Smoke Test

After installing the Phase 7B APK in Remote Access:

1. Launch `QPNPU Hardware Probe`.
2. Tap `Toy Decode`.
3. Verify the UI shows Android toy decode JSON and the app does not crash.
4. Confirm logcat contains:

```text
QPNPU_TOY_DECODE_JSON_BEGIN
QPNPU_TOY_DECODE_JSON_END
```

5. Download logcat and extract:

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind toy_decode \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_toy_decode_<date>.json
```

6. Optionally preserve all button-tap payloads from the same session:

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind all \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_probe_<date>.all_qpnpu_payloads.json
```

Record:

- Whether the APK installed and launched.
- Whether `Toy Decode` emitted `source: android-toy-decode`.
- Prompt token IDs and generated token IDs.
- Embedded benchmark validation status.
- Any Java warnings or native errors.
- The Device Farm device name/model, Android version, session ARN, screenshots, and log artifacts.

This validates APK asset packaging and Android native CPU reference decode plumbing only. The toy model is not Qwen 9B, the tokenizer is a byte stub, execution is not NPU/QNN/NNAPI/Vulkan, and toy throughput is not a trial performance claim.

## Phase 7C Generated Kernel Candidate Smoke Test

After installing the Phase 7C APK in Remote Access:

1. Launch `QPNPU Hardware Probe`.
2. Tap `Gen Kernels`.
3. Verify the UI shows generated-kernel candidate JSON and the app does not crash.
4. Confirm logcat contains:

```text
QPNPU_PHASE7C_JSON_BEGIN
QPNPU_PHASE7C_JSON_END
```

5. Download logcat and extract:

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind phase7c \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_phase7c_<date>.json
```

6. Optionally preserve all button-tap payloads from the same session:

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind all \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_probe_<date>.all_qpnpu_payloads.json
```

Record:

- Whether the APK installed and launched.
- Whether `Gen Kernels` emitted `source: android-phase7c-generated-kernels`.
- Candidate names, statuses, target features, and correctness flags.
- Whether any candidate returned `sigill`.
- Which candidates were skipped or deferred.
- Device Farm device name/model, Android version, session ARN, screenshots, and log artifacts.

This validates generated native CPU candidate plumbing only. It is not Qwen 9B inference, not QNN/NPU/NNAPI/Vulkan execution, and not a tokens/sec performance claim.


## Phase 8 External Toy Model Delivery Smoke Test

After installing the Phase 8 APK in Remote Access:

1. Launch `QPNPU Hardware Probe`.
2. Leave the manifest URL blank for the bundled tiny fallback, or paste an HTTPS URL to a hosted Phase 8 `manifest.json`.
3. Tap `External Model`.
4. Verify the UI shows `source: android-phase8-external-model-demo`.
5. Verify `model_delivery.all_sha256_verified` is `true`.
6. Confirm logcat contains:

```text
QPNPU_PHASE8_JSON_BEGIN
QPNPU_PHASE8_JSON_END
```

7. Download logcat and extract:

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind phase8 \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_phase8_<date>.json
```

Record:

- Whether the APK installed and launched.
- Whether the manifest source was `bundled_asset_manifest` or `url`.
- Cache directory and file count.
- Whether every file verified SHA-256.
- Generated token IDs from the nested toy decode result.
- Any network/download/cache errors.

This validates external-style artifact delivery and cached toy decode only. It is not Qwen 9B inference, not accelerator execution, and not a tokens/sec performance claim.
