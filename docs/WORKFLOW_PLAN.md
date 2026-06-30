# Workflow Plan

This repository is currently in Phase 1. Each phase should leave behind a small, testable checkpoint.

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

Start AWS Device Farm remote access after a minimal Android probe APK or test runner exists, not after the host-side-only probe and not after the full inference library.

## Phase 2: Native CPU Reference Backend And Microbench Foundation

Exit criteria:

- Native CPU backend can execute tiny fixture operators.
- CPU output is used as correctness reference.
- Native test harness runs without Android first.
- Microbenchmark result JSON can be produced from local native runs.

## Phase 3: Model Metadata Pipeline

Exit criteria:

- Tiny fixture model metadata can be read and validated.
- Conversion planning produces deterministic QPNPU metadata.
- No large model weights are committed.

## Phase 4: Android Probe App Or Native Android Harness

Exit criteria:

- Minimal Android probe APK or test runner exists.
- Device-side NNAPI and runtime library enumeration can be performed without claiming accelerator execution.
- ADB scripts can install or invoke the probe on a connected device.
- Probe schema remains backward compatible with Phase 1 host-side outputs.

## Phase 5: Quantization Validation

Exit criteria:

- Int4 groupwise quantization is validated on small fixtures.
- Quantized tensor metadata records scales, shapes, and packing order.
- Accuracy checks compare against CPU reference fixtures.

## Phase 6: Kernel Generation

Exit criteria:

- Kernel generator emits deterministic candidate kernels from configs.
- Generated kernels build in the native project.
- Microbenchmarks can compare candidates on local CPU and Android.

## Phase 7: Android Benchmark Harness

Exit criteria:

- Benchmark runner deploys through ADB.
- Results are pulled as benchmark JSON.
- Thermal and device state are captured with every run.

## Phase 8: Backend Capability Selection

Exit criteria:

- Probe data drives conservative backend selection.
- CPU fallback always works.
- Vulkan, NNAPI, and QNN paths are only enabled when runtime capability is detected.

## Phase 9: AWS Device Farm Runs And Full Trial Analysis

Exit criteria:

- Device Farm scripts can create projects, upload artifacts, and schedule runs with user-provided credentials.
- Runs produce repeatable probe and benchmark artifacts.
- Configurable Qwen-style 9B trial runs on real target hardware.
- Results are reproducible and include thermal context.
- Any decode tokens/sec claims are backed by recorded benchmark artifacts.