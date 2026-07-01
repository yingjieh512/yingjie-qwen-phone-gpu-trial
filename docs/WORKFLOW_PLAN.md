# Workflow Plan

This repository is currently completing Phase 4B. Each phase should leave behind a small, testable checkpoint.

## Phase 0: Repository Skeleton

Exit criteria:

- Directory structure exists.
- Python tests pass locally.
- CLI scripts provide useful help or dry-run output.
- No Android device, AWS credentials, Qualcomm SDK, or model download is required.

## Phase 1: Host-Side ADB Hardware Probe

Exit criteria:

- `scripts/adb/collect_device_info.sh` validates `adb` and connected-device state.
- A connected device probe collects raw `getprop`, `uname`, CPU, memory, thermal, sysfs CPU, GPU-hint, and NPU-hint files.
- The parser builds a valid `probe_result.json` and updates `benchmarks/results/latest_probe.json`.
- Probe summarization prints backend hints and a conservative backend order.
- Tests cover parser behavior with synthetic raw ADB fixtures and do not require an Android device.
- No Android APK is required yet.

## Phase 2: Native CPU Reference Backend And Microbench Foundation

Exit criteria:

- Native CMake configure/build/test passes on a machine with CMake and a C++17 compiler.
- CPU reference kernels pass correctness tests for fp32 matvec, int4 matvec, RMSNorm, RoPE, and softmax.
- CPU backend reports available.
- Vulkan, NNAPI, and QNN backends remain unavailable stubs with non-empty reasons.
- Local CPU microbench emits valid benchmark JSON.
- No Android device, AWS credentials, Qualcomm SDK, model download, or NPU execution is required.

## Phase 3: Local Toy Model Vertical Slice

Exit criteria:

- A tiny deterministic QPNPU toy model can be created locally.
- `metadata.json`, `model.bin`, `tokenizer_stub.json`, and artifact `README.md` are written.
- QPNPU metadata validates and fp32 tensors can be loaded by name.
- The toy model can be inspected with `scripts/model/inspect_model.py --model-dir`.
- CPU-only toy decode can run from a prompt and write JSON with an embedded benchmark object.
- The embedded benchmark validates with `qpnpu.benchmark.validate_benchmark_result`.
- No Android hardware, AWS credentials, Qualcomm SDK, Hugging Face credentials, network access, large model, or NPU execution is required.
- Warnings clearly state that toy results are not Qwen 9B, not Android, not NPU, and not performance claims.

## Phase 4A: Minimal Android Probe APK

Exit criteria:

- A minimal Android app project exists under `android/probe-app`.
- A debug APK can be built with Android Studio or a local Gradle/Android SDK setup.
- The package name is `com.qpnpu.trial`.
- The UI has `QPNPU Probe`, a `Run Probe` button, scrollable JSON output, `Copy JSON`, and `Clear` controls.
- Tapping `Run Probe` collects best-effort Android-side hardware info.
- Probe JSON is shown on screen.
- Probe JSON is logged to logcat between `QPNPU_PROBE_JSON_BEGIN` and `QPNPU_PROBE_JSON_END`.
- The app tries to save `getExternalFilesDir(null)/probe_result.json`.
- The app requires no special permissions.
- The project is ready for the first AWS Device Farm Remote Access session.

The first AWS Remote Access session may start after Phase 4A. It does not need full native kernels, the Phase 3 toy model, or any full-model path. The goal is hardware/app smoke validation, not performance.

## Phase 4B: First AWS Remote Access Smoke Session

Exit criteria:

- The Phase 4A debug APK is uploaded or installed in a manual Remote Access session.
- The app launches and runs the probe on a selected Android device.
- UI JSON and logcat markers are observed.
- Session metadata, logs, and copied probe JSON are saved when available.
- The Android probe JSON can be summarized into a target hardware profile.
- No automated benchmark or performance claim is made.

Phase 4B result:

- `benchmarks/results/aws_remote_probe_2026-07-01.json` records the first S26 Ultra probe.
- `benchmarks/results/aws_remote_probe_2026-07-01.summary.json` records the compact summary.
- `docs/TARGET_HARDWARE_PROFILE.md` records the human-readable hardware profile.
- `docs/PHASE_4B_RESULTS.md` records the checkpoint interpretation.

## Phase 5: Android Native CPU Microbenchmark Harness

Exit criteria:

- The Android probe app can load a small Java/JNI/NDK native library.
- Native CPU kernels for fp32 matvec, int4 dequant matvec, RMSNorm, RoPE, and softmax run on Android.
- Results are checked against small deterministic expected outputs.
- Benchmark JSON is shown on screen and emitted to logcat.
- Thermal state from the probe path is included with benchmark JSON.
- No Qwen 9B model, QNN SDK, NPU execution, or performance target claim is required.

## Phase 6: Quantization Validation

Exit criteria:

- Int4 groupwise quantization is validated on small fixtures.
- Quantized tensor metadata records scales, shapes, and packing order.
- Accuracy checks compare against CPU reference fixtures.

## Phase 7: Kernel Generation

Exit criteria:

- Kernel generator emits deterministic candidate kernels from configs.
- Generated kernels build in the native project.
- Microbenchmarks can compare candidates on local CPU and Android.

## Phase 8: Android Benchmark Harness

Exit criteria:

- Benchmark runner deploys through ADB.
- Results are pulled as benchmark JSON.
- Thermal and device state are captured with every run.

## Phase 9: Backend Capability Selection

Exit criteria:

- Probe data drives conservative backend selection.
- CPU fallback always works.
- Vulkan, NNAPI, and QNN paths are only enabled when runtime capability is detected.

## Phase 10: AWS Device Farm Runs And Full Trial Analysis

Exit criteria:

- Device Farm scripts can create projects, upload artifacts, and schedule runs with user-provided credentials.
- Runs produce repeatable probe and benchmark artifacts.
- Configurable Qwen-style 9B trial runs on real target hardware.
- Results are reproducible and include thermal context.
- Any decode tokens/sec claims are backed by recorded benchmark artifacts.