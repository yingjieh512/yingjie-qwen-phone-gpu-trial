# qwen-phone-npu-trial

Repository for a Snapdragon-class Android phone NPU trial with a configurable Qwen-style 9B decoder model.

The trial target is a Samsung Galaxy S26 Ultra-class Android phone with a Snapdragon-class SoC. The trial brief mentions "Snapdragon X Elite NPU", but actual CPU, GPU, NNAPI, QNN, and NPU capabilities must be detected at runtime before any backend is selected.

The long-term performance target is at least 20 decode tokens/sec. No performance target has been measured or achieved yet.

## Current Status

Phase 7B adds an Android packaged toy decode smoke path. The APK carries a tiny deterministic QPNPU toy model asset and runs a native CPU/JNI reference decode-like loop, then displays and logs JSON. It is not Qwen 9B, not the Qwen tokenizer, not QNN/NPU/Vulkan/NNAPI execution, and not a performance-target benchmark.

Phase 7A adds guarded ARM ISA instruction probes from the Android app process. It validates selected reported CPU features with tiny SIGILL-guarded fixtures and still does not run Qwen 9B, QNN, Vulkan kernels, NPU execution, or performance-target benchmarks.

Phase 6 adds on-device Android characterization for CPU ISA evidence, thread scaling, memory bandwidth, quantization packing, and backend library load probes. It still does not run Qwen 9B, QNN, Vulkan kernels, or NPU execution.

Phase 5 adds a minimal Android NDK/JNI native CPU microbenchmark harness inside the probe APK. The app can run tiny deterministic native fixtures for fp32 matvec, int4 dequant matvec, RMSNorm, softmax, and RoPE, then display and log benchmark-schema JSON. These are CPU-only harness checks, not Qwen 9B inference, not NPU/QNN execution, and not performance target claims.

Phase 4A/4B added the Android probe APK and first AWS Device Farm Remote Access smoke path. The APK displays best-effort hardware probe JSON on screen, logs it to logcat between clear markers, and tries to save it to app-private external files.

Phase 3 adds a local runnable vertical slice: a tiny deterministic CPU-only toy Qwen-like artifact can be created, inspected, decoded, and written as benchmark-schema JSON without Android hardware, AWS, Hugging Face credentials, Qualcomm QNN SDKs, or model downloads.

This repository currently contains:

- Python helpers for config loading, schema validation, benchmark selection, kernel config hashing, model metadata validation/loading, lightweight int4 quantization, and ADB probe parsing.
- A minimal Android probe app package named `com.qpnpu.trial` for manual Remote Access smoke validation.
- A tiny QPNPU toy model creator and CPU Python reference runtime for local smoke tests.
- A host-side ADB collection script from Phase 1 that writes structured probe JSON from a connected debugging-enabled Android device.
- Native CPU reference kernels for fp32 matvec, groupwise symmetric int4 dequant matvec, RMSNorm, RoPE, and softmax.
- Backend classes where CPU reports available and Vulkan, NNAPI, and QNN report unavailable with explicit Phase 2 reasons.
- A local CPU microbenchmark executable that emits benchmark-schema JSON with warnings that results are not phone or NPU claims.
- GitHub Actions CI for Python tests, native CMake build, CTest, and microbench smoke.

This phase does not implement:

- Qwen 9B inference.
- A production Android inference app.
- Real AWS Device Farm automated runs.
- Real Qualcomm QNN integration.
- Real Vulkan, NNAPI, QNN, or NPU execution.
- Model downloads.
- Performance target claims.

## Quickstart

From the repository root:

```bash
python -m pytest tests
python tools/probe_parser/summarize_probe.py benchmarks/results/sample_probe.json
python tools/kernelgen/generate_kernels.py --probe benchmarks/results/sample_probe.json --config configs/kernel_config.example.json --out native/kernels/generated
python scripts/autotune/run_autotune.py --dry-run
```


## Phase 7B Android Toy Decode Quickstart

Build the APK:

```powershell
cd android\probe-app
.\gradlew.bat assembleDebug
```

In AWS Device Farm Remote Access, upload/install the APK, launch `QPNPU Hardware Probe`, and tap `Toy Decode`. The app logs Android toy decode JSON between:

```text
QPNPU_TOY_DECODE_JSON_BEGIN
QPNPU_TOY_DECODE_JSON_END
```

Extract it from downloaded logcat:

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind toy_decode \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_toy_decode_<date>.json
```

Phase 7B proves tiny model asset packaging, JNI tensor loading, deterministic CPU reference math, UI/logcat output, and extraction. It is not real Qwen 9B inference and does not use or measure the phone NPU.

## Phase 7A Guarded ISA Probe Quickstart

Build the APK:

```powershell
cd android\probe-app
.\gradlew.bat assembleDebug
```

In AWS Device Farm Remote Access, upload/install the APK, launch `QPNPU Hardware Probe`, and tap `ISA Probe`. The app logs guarded ISA probe JSON between:

```text
QPNPU_PHASE7A_JSON_BEGIN
QPNPU_PHASE7A_JSON_END
```

Extract it from downloaded logcat:

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind phase7a \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_phase7a_<date>.json
```

Phase 7A records executable CPU ISA smoke evidence only. A successful probe means one tiny guarded instruction fixture ran; it is not full kernel correctness, accelerator execution, Qwen 9B inference, or a performance claim.

## Phase 6 Android Characterization Quickstart

Build the APK:

```powershell
cd android\probe-app
.\gradlew.bat assembleDebug
```

In AWS Device Farm Remote Access, upload/install the APK, launch `QPNPU Hardware Probe`, and tap `Characterize HW`. The app logs characterization JSON between:

```text
QPNPU_PHASE6_JSON_BEGIN
QPNPU_PHASE6_JSON_END
```

Extract it from downloaded logcat:

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind phase6 \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_phase6_<date>.json
```


To preserve every QPNPU payload from repeated button taps in one Device Farm session, extract a bundled artifact too:

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind all \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_probe_<date>.all_qpnpu_payloads.json
```
Phase 6 records CPU ISA evidence, thread scaling, memory copy fixtures, int4 packing validation, and backend `dlopen` results. These are characterization signals only, not accelerator execution or performance claims.
## Phase 5 Android Native Microbenchmark Quickstart

Build the debug APK with the NDK/JNI harness:

```powershell
cd android\probe-app
.\gradlew.bat assembleDebug
```

Find the built APK:

```bash
python scripts/android/find_probe_apk.py
```

In AWS Device Farm Remote Access, upload/install the APK, launch `QPNPU Hardware Probe`, and tap `Native Bench` to run the standalone native CPU microbenchmarks. The app logs native benchmark JSON between:

```text
QPNPU_NATIVE_BENCH_JSON_BEGIN
QPNPU_NATIVE_BENCH_JSON_END
```

Extract the native benchmark JSON from downloaded logcat:

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind native \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_native_microbench_<date>.json
```

The native fixtures validate packaging, JNI, timing, and result extraction only. They are not Qwen 9B inference, not NPU/QNN execution, and not a performance claim.
## Phase 4A Android Probe APK Quickstart

Build the debug APK with Android Studio or an installed Gradle/Android SDK:

```bash
cd android/probe-app
./gradlew assembleDebug
```

On Windows:

```powershell
cd android\probe-app
.\gradlew.bat assembleDebug
```

Find the built APK:

```bash
python scripts/android/find_probe_apk.py
```

For the first AWS Device Farm Remote Access smoke test, upload or install the debug APK, launch `QPNPU Hardware Probe`, tap `Run Probe`, and verify that JSON appears in the UI and logcat contains `QPNPU_PROBE_JSON_BEGIN` and `QPNPU_PROBE_JSON_END`.

Save copied probe JSON as:

```text
benchmarks/results/aws_remote_probe_<date>.json
```

Do not treat this Remote Access smoke test as a benchmark or performance claim.

## Phase 3 Toy Model Quickstart

Create the local toy model artifact:

```bash
python scripts/model/create_toy_qwen.py --out models/toy_qwen_smoke --overwrite
```

Inspect the QPNPU metadata and tensor manifest:

```bash
python scripts/model/inspect_model.py --model-dir models/toy_qwen_smoke
```

Run deterministic CPU-only toy decode and write benchmark JSON:

```bash
python scripts/model/run_toy_decode.py \
  --model-dir models/toy_qwen_smoke \
  --prompt "hello" \
  --max-new-tokens 8 \
  --out benchmarks/results/toy_decode_smoke.json
```

This is only a local workflow smoke test. The toy model is not Qwen 9B, does not use the Qwen tokenizer, does not run on Android, does not use an NPU or QNN, and does not measure or achieve the 20 decode tokens/sec target.

## Phase 1 ADB Probe Quickstart

With Android platform-tools installed and USB debugging enabled on a connected device:

```bash
bash scripts/adb/collect_device_info.sh
python tools/probe_parser/summarize_probe.py benchmarks/results/latest_probe.json
```

Optional output directory:

```bash
bash scripts/adb/collect_device_info.sh --out benchmarks/results/my_probe
```

If multiple devices are connected, set `ANDROID_SERIAL` before running the script.

## Phase 2 Native Quickstart

Build and test the native foundation:

```bash
cmake -S native -B native/build
cmake --build native/build --config Release
ctest --test-dir native/build --build-config Release --output-on-failure
```

Run one local CPU microbenchmark:

```bash
./native/build/qpnpu_microbench --operator int4_matvec --rows 256 --cols 256 --group-size 128 --iters 20 --out benchmarks/results/local_int4_matvec.json
```

On multi-config generators such as Visual Studio, the executable may be under `native/build/Debug/qpnpu_microbench.exe` or `native/build/Release/qpnpu_microbench.exe`.

Run the Python wrapper for the small Phase 2 operator suite:

```bash
python scripts/native/run_local_microbench.py --build-dir native/build --out benchmarks/results/local_microbench.json
```

## Phase 2.1 Verification

Use the local verifier:

```bash
python scripts/dev/verify_phase2.py
```

If your machine lacks CMake or a C++ compiler, native verification is reported as `BLOCKED`, not as a source failure. Python-only verification is available with:

```bash
python scripts/dev/verify_phase2.py --skip-native
```

GitHub Actions CI is defined in `.github/workflows/ci.yml`. After pushing a branch, check the repository Actions tab for the `CI` workflow. CI runs Python tests, native CMake configure/build, CTest, and local CPU microbench smoke on `ubuntu-latest`.

AWS Remote Access may start after Phase 4A for manual app/hardware smoke validation. Automated Device Farm runs should wait until an instrumentation or test runner exists.

## What Works Locally

- Python unit tests run without Android hardware, AWS credentials, Qualcomm SDKs, or network access.
- A minimal Android probe app project exists under `android/probe-app` with an NDK/JNI CPU microbenchmark harness and a packaged toy decode asset smoke path.
- A toy QPNPU model can be created, inspected, decoded with a CPU Python reference path, and emitted as benchmark JSON.
- Sample probe JSON can be validated and summarized.
- ADB raw-output fixtures validate the Phase 1 parser path without requiring a real device.
- Native CPU reference kernels can be built and tested with CMake on a machine with CMake and a C++17 compiler.
- Local CPU microbenchmarks can produce benchmark-schema JSON.
- The verifier clearly distinguishes PASS, FAIL, and BLOCKED native checks.
- Example kernel config can be validated and used to generate a tiny placeholder C++ file.

## What Is Stubbed

- The Android probe APK does not run real Qwen inference, QNN, or NPU code; Phase 5 native microbenchmarks and Phase 7B toy decode are tiny CPU-only harness checks.
- The Phase 3 toy runtime is not a transformer and is not Qwen 9B inference.
- Vulkan, NNAPI, and QNN backends are safe unavailable stubs.
- AWS Device Farm scripts only check for `aws`, print usage, and show intended commands.
- Generated kernels remain placeholders.
- No Qwen 9B, accelerator, or NPU benchmark exists; Phase 5 and Phase 7B only validate native CPU execution and model-asset plumbing.

## Next Phases

1. Phase 7C: Generated native CPU kernel candidates gated by Phase 7A ISA evidence and Phase 5 correctness fixtures.
2. Phase 8: Backend probing for NNAPI, Vulkan, and QNN availability with conservative CPU fallback.
3. Phase 9: Automated Android/Device Farm benchmark runs once a test runner exists.
4. Phase 10: Full model integration analysis with recorded artifacts before any tokens/sec claim.
