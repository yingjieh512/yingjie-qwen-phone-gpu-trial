# Workflow Plan

This repository is currently in Phase 0. Each later phase should leave behind a small, testable checkpoint.

## Phase 0: Repository Skeleton

Exit criteria:

- Directory structure exists.
- Python tests pass locally.
- CLI scripts provide useful help or dry-run output.
- No Android device, AWS credentials, Qualcomm SDK, or model download is required.

## Phase 1: ADB Hardware Probe

Exit criteria:

- Minimal Android probe APK or test runner exists.
- ADB scripts can install or invoke the probe on a connected device.
- Probe JSON captures device, CPU, memory, GPU, NNAPI, QNN, NPU-related, thermal, and warning fields.
- Probe schema remains backward compatible with Phase 0 samples.

Start AWS Device Farm remote access after this phase has a minimal Android probe APK/test runner. Do not wait for the full inference library.

## Phase 2: CPU Reference Backend

Exit criteria:

- Native CPU backend can execute tiny fixture operators.
- CPU output is used as correctness reference.
- Native test harness runs without Android first, then on Android.

## Phase 3: Model Metadata Pipeline

Exit criteria:

- Tiny fixture model metadata can be read and validated.
- Conversion planning produces deterministic QPNPU metadata.
- No large model weights are committed.

## Phase 4: Quantization Validation

Exit criteria:

- Int4 groupwise quantization is validated on small fixtures.
- Quantized tensor metadata records scales, shapes, and packing order.
- Accuracy checks compare against CPU reference fixtures.

## Phase 5: Kernel Generation

Exit criteria:

- Kernel generator emits deterministic candidate kernels from configs.
- Generated kernels build in the native project.
- Microbenchmarks can compare candidates on local CPU and Android.

## Phase 6: Android Benchmark Harness

Exit criteria:

- Benchmark runner deploys through ADB.
- Results are pulled as benchmark JSON.
- Thermal and device state are captured with every run.

## Phase 7: Backend Capability Selection

Exit criteria:

- Probe data drives conservative backend selection.
- CPU fallback always works.
- Vulkan, NNAPI, and QNN paths are only enabled when runtime capability is detected.

## Phase 8: AWS Device Farm Runs

Exit criteria:

- Device Farm scripts can create projects, upload artifacts, and schedule runs with user-provided credentials.
- Runs produce repeatable probe and benchmark artifacts.
- Remote access is used to inspect device-specific failures.

## Phase 9: Full Trial and Analysis

Exit criteria:

- Configurable Qwen-style 9B trial runs on real target hardware.
- Results are reproducible and include thermal context.
- Any decode tokens/sec claims are backed by recorded benchmark artifacts.

