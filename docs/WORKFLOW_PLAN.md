# Workflow Plan

This repository has completed the Phase 9 native cached-shard loader smoke path and is preparing for layer-slice correctness work. Each phase should leave behind a small, testable checkpoint.

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

- The Android probe app loads a small Java/JNI/NDK native library named `qpnpu_probe_native`.
- Native CPU fixtures for fp32 matvec, int4 dequant matvec, RMSNorm, RoPE, and softmax run from the APK.
- Results are checked against small deterministic expected outputs.
- Full probe JSON embeds a `microbenchmarks` object when the native library is available.
- Standalone native benchmark JSON is shown on screen when `Native Bench` is tapped.
- Native benchmark JSON is emitted to logcat between `QPNPU_NATIVE_BENCH_JSON_BEGIN` and `QPNPU_NATIVE_BENCH_JSON_END`.
- Native benchmark JSON can be extracted from logcat and validated with the existing benchmark schema helpers.
- No Qwen 9B model, QNN SDK, NPU execution, or performance target claim is required.

Phase 5 result:

- `android/probe-app/app/src/main/cpp/qpnpu_probe_native.cpp` implements tiny deterministic native CPU benchmark fixtures.
- `android/probe-app/app/src/main/java/com/qpnpu/trial/MainActivity.java` exposes `Native Bench` and embeds native microbenchmarks in the full probe flow.
- `scripts/android/extract_probe_json_from_logcat.py --kind native` extracts native benchmark JSON from Device Farm logcat.
- `docs/PHASE_5_NATIVE_MICROBENCH.md` records the runbook and interpretation guardrails.

## Phase 6: On-Device CPU ISA, Topology, Quantization, And Backend Load Probes

Exit criteria:

- The Android APK exposes a `Phase 6` action.
- Phase 6 JSON is logged between `QPNPU_PHASE6_JSON_BEGIN` and `QPNPU_PHASE6_JSON_END`.
- CPU ISA evidence compares `/proc/cpuinfo` with auxv feature bits where available.
- Thread scaling, app-visible affinity, and bounded memory-copy probes run from JNI.
- Tiny int4 quantization fixture validates packing/dequant metadata and correctness.
- Backend load probes use controlled `dlopen` only and do not execute accelerator kernels.
- Host extraction supports `--kind phase6` and validates the JSON.
- No Qwen 9B, QNN/NPU execution, or performance claim is made.

Phase 6 result:

- `android/probe-app/app/src/main/cpp/qpnpu_phase6_native.cpp` implements native characterization probes.
- `qpnpu/android_phase6.py` validates Phase 6 payloads.
- `scripts/android/extract_probe_json_from_logcat.py --kind phase6` extracts Phase 6 logcat payloads.
- `docs/PHASE_6_ANDROID_CHARACTERIZATION.md` records the runbook and interpretation guardrails.


## Phase 7A: Guarded ARM ISA Probes

Exit criteria:

- The Android APK exposes an `ISA Probe` action.
- Phase 7A JSON is logged between `QPNPU_PHASE7A_JSON_BEGIN` and `QPNPU_PHASE7A_JSON_END`.
- The native library compares reported CPU features from `/proc/cpuinfo` and auxv with tiny executable instruction fixtures.
- Feature-specific probes are guarded with SIGILL handling and run only when the feature is reported.
- Skipped, deferred, successful, and SIGILL outcomes are represented in JSON.
- Host extraction supports `--kind phase7a` and validates the JSON.
- No Qwen 9B, QNN/NPU execution, or performance claim is made.

Phase 7A result:

- `android/probe-app/app/src/main/cpp/qpnpu_phase7a_native.cpp` implements guarded ARM ISA probes.
- `qpnpu/android_phase7a.py` validates Phase 7A payloads.
- `scripts/android/extract_probe_json_from_logcat.py --kind phase7a` extracts Phase 7A logcat payloads.
- `docs/PHASE_7A_GUARDED_ISA_PROBES.md` records the runbook and guardrails.

## Phase 7B: Android Toy Decode Asset Smoke

Exit criteria:

- The Android APK exposes a `Toy Decode` action.
- A tiny deterministic QPNPU toy model is packaged under app assets.
- Native JNI code loads toy metadata and tensor bytes from assets.
- The native path runs a deterministic CPU reference decode-like loop for prompt `hello`.
- Toy decode JSON is displayed, saved best-effort, and logged between `QPNPU_TOY_DECODE_JSON_BEGIN` and `QPNPU_TOY_DECODE_JSON_END`.
- Host extraction and validation tests pass without Android hardware.
- No real Qwen 9B, QNN/NPU execution, or performance claim is made.

Phase 7B result:

- `android/probe-app/app/src/main/assets/toy_qwen_7b/` contains the packaged toy model.
- `android/probe-app/app/src/main/cpp/qpnpu_toy_decode_native.cpp` implements Android native toy decode.
- `qpnpu/android_toy_decode.py` validates toy decode payloads.
- `scripts/android/extract_probe_json_from_logcat.py --kind toy_decode` extracts Phase 7B logcat payloads.
- `docs/PHASE_7B_ANDROID_TOY_DECODE.md` records the runbook and guardrails.

## Phase 7C: Generated Native CPU Kernel Candidates

Exit criteria:

- The Android APK exposes a `Gen Kernels` action.
- A native generated-candidate harness builds into `qpnpu_probe_native`.
- Tiny deterministic candidates run only when their target feature is reported, except scalar baseline.
- Executed candidates compare against deterministic references and report per-candidate correctness.
- SVE2, SVEI8MM, and SME are represented as deferred experimental candidates unless a safer isolated runner exists.
- Phase 7C JSON is logged between `QPNPU_PHASE7C_JSON_BEGIN` and `QPNPU_PHASE7C_JSON_END`.
- Host extraction and validation tests pass without Android hardware.
- No real Qwen 9B, QNN/NPU execution, or performance claim is made.

Phase 7C result:

- `android/probe-app/app/src/main/cpp/qpnpu_phase7c_native.cpp` implements generated native candidate fixtures.
- `qpnpu/android_phase7c.py` validates Phase 7C payloads.
- `scripts/android/extract_probe_json_from_logcat.py --kind phase7c` extracts Phase 7C logcat payloads.
- `docs/PHASE_7C_GENERATED_KERNELS.md` records the runbook and guardrails.

## Phase 7D: Kernel Generation Iteration

Exit criteria:

- Kernel generator emits deterministic candidate kernels from configs.
- Generated kernels build in the native project.
- Microbenchmarks can compare candidates on local CPU and Android.

## Phase 8: External Toy Model Delivery Demo

Exit criteria:

- A QPNPU sharded toy model manifest schema exists for externally delivered artifacts.
- `scripts/model/create_external_toy_artifact.py` creates a tiny manifest plus shard artifact locally.
- The Android APK exposes an `External Model` action.
- Blank manifest URL uses a bundled tiny manifest fallback; non-empty HTTP(S) URL downloads a hosted manifest.
- Manifest files are cached in app-private storage and verified with SHA-256.
- Cached toy model bytes feed the Android native toy decode path.
- Phase 8 JSON is displayed and logged between `QPNPU_PHASE8_JSON_BEGIN` and `QPNPU_PHASE8_JSON_END`.
- Host extraction supports `--kind phase8` and validates the JSON.
- No real Qwen 9B, Hugging Face credentials on device, QNN/NPU execution, or performance claim is made.

Phase 8 result:

- `qpnpu/model_artifact.py` validates external toy model manifests.
- `qpnpu/android_phase8.py` validates Android Phase 8 payloads.
- `android/probe-app/app/src/main/assets/phase8_external_toy_manifest.json` provides a no-network fallback demo.
- `docs/PHASE_8_EXTERNAL_MODEL_DELIVERY.md` records the runbook and guardrails.

## Phase 9: Android Native Cached-Shard Loader

Exit criteria:

- Native code opens verified shards from app-private storage.
- Tensor ranges can be mmaped or streamed without passing the whole artifact through the Java heap.
- A tiny external toy model loads from downloaded shards instead of APK assets.
- Tokenizer and metadata loading remain deterministic.
- Phase 9 JSON is logged between `QPNPU_PHASE9_JSON_BEGIN` and `QPNPU_PHASE9_JSON_END`.
- Host extraction supports `--kind phase9` and validates the JSON.
- No real Qwen 9B, QNN/NPU execution, or performance claim is made.

Phase 9 result:

- `android/probe-app/app/src/main/cpp/qpnpu_toy_decode_native.cpp` exposes a native file-loader entry point that opens metadata and mmap-reads shard files.
- `android/probe-app/app/src/main/java/com/qpnpu/trial/MainActivity.java` exposes the `Shard Load` action and emits Phase 9 JSON.
- `qpnpu/android_phase9.py` validates native shard-loader payloads.
- `scripts/android/extract_probe_json_from_logcat.py --kind phase9` extracts Phase 9 logcat payloads.
- `docs/PHASE_9_NATIVE_SHARD_LOADER.md` records the runbook and guardrails.

## Phase 10: Layer-Slice Correctness Ladder

Exit criteria:

- Offline tools export one small Qwen-like layer slice in QPNPU format.
- Android CPU reference runs embedding, RMSNorm, linear/matvec, RoPE, softmax, and MLP slice checks.
- Each operator and layer slice compares against Python reference outputs.
- No speed or NPU claim is made.

## Phase 11: Quantized Operator Expansion

Exit criteria:

- Int4/int8 tensor block formats match the offline converter.
- Generated CPU kernels cover the exact matmul/dequant shapes needed by the model.
- Every operator validates against Python reference fixtures.
- CPU fallback remains mandatory.

## Phase 12: Backend API Enumeration

Exit criteria:

- Vulkan and NNAPI capabilities are queried through real APIs, not just library-name hints.
- QNN is attempted only if a legally usable Qualcomm SDK/runtime path is available.
- Capability JSON drives conservative backend selection.
- No NPU availability is claimed from string hints alone.

## Phase 13: First Accelerator-Backed Subgraph

Exit criteria:

- One tiny supported op or subgraph runs through Vulkan, NNAPI, or QNN if available.
- Output is compared against CPU reference.
- Unsupported ops fall back to CPU.
- Backend, shape, correctness, and thermal context are recorded.

## Phase 14: Progressive Model Scale-Up

Exit criteria:

- External artifact checks progress through tiny fake shards, toy model, one-layer slice, small real model, larger real model, then quantized 9B.
- For 9B, load and one-token decode correctness are proven before throughput work.
- Memory, storage, thermal, and failure modes are captured at every scale.

## Phase 15: Automated Device Farm Regression

Exit criteria:

- Manual tapping is replaced with an instrumentation or command-driven test runner.
- APK upload, bounded test execution, log/artifact retrieval, and JSON validation are automated.
- Large model tests remain optional and externally configured.

## Phase 16: Full Trial Analysis And Performance Gate

Exit criteria:

- A configurable Qwen-style 9B trial runs on the real target with recorded artifact hashes and backend config hashes.
- Decode throughput is measured only after correctness gates pass.
- Results are reproducible and include thermal context.
- Any `>=20` decode tokens/sec claim is backed by recorded benchmark artifacts from the full real model path.

See `docs/QWEN_9B_DEVICE_FARM_PLAN.md` for the runtime model delivery strategy. The APK should not embed the real 9B model.
