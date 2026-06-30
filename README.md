# qwen-phone-npu-trial

Repository for a Snapdragon-class Android phone NPU trial with a configurable Qwen-style 9B decoder model.

The trial target is a Samsung Galaxy S26 Ultra-class Android phone with a Snapdragon-class SoC. The trial brief mentions "Snapdragon X Elite NPU", but actual CPU, GPU, NNAPI, QNN, and NPU capabilities must be detected at runtime before any backend is selected.

The long-term performance target is at least 20 decode tokens/sec. No performance target has been measured or achieved yet.

## Current Status

Phase 3 adds a local runnable vertical slice: a tiny deterministic CPU-only toy Qwen-like artifact can be created, inspected, decoded, and written as benchmark-schema JSON without Android hardware, AWS, Hugging Face credentials, Qualcomm QNN SDKs, or model downloads.

Phase 2.1 still hardens native verification: CI validates the Python and native Phase 2 paths on Ubuntu, and `scripts/dev/verify_phase2.py` explains whether local native checks pass or are blocked by missing CMake/compiler tools.

This repository currently contains:

- Python helpers for config loading, schema validation, benchmark selection, kernel config hashing, model metadata validation/loading, lightweight int4 quantization, and ADB probe parsing.
- A tiny QPNPU toy model creator and CPU Python reference runtime for local smoke tests.
- A host-side ADB collection script from Phase 1 that writes structured probe JSON from a connected debugging-enabled Android device.
- Native CPU reference kernels for fp32 matvec, groupwise symmetric int4 dequant matvec, RMSNorm, RoPE, and softmax.
- Backend classes where CPU reports available and Vulkan, NNAPI, and QNN report unavailable with explicit Phase 2 reasons.
- A local CPU microbenchmark executable that emits benchmark-schema JSON with warnings that results are not phone or NPU claims.
- GitHub Actions CI for Python tests, native CMake build, CTest, and microbench smoke.

This phase does not implement:

- Android APK logic.
- Real inference execution for a full model.
- Real AWS Device Farm runs.
- Real Qualcomm QNN integration.
- Real Vulkan, NNAPI, QNN, or NPU execution.
- Model downloads.
- Qwen 9B inference.
- Performance target claims.

## Quickstart

From the repository root:

```bash
python -m pytest tests
python tools/probe_parser/summarize_probe.py benchmarks/results/sample_probe.json
python tools/kernelgen/generate_kernels.py --probe benchmarks/results/sample_probe.json --config configs/kernel_config.example.json --out native/kernels/generated
python scripts/autotune/run_autotune.py --dry-run
```

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

AWS Remote Access timing is unchanged: start AWS Device Farm remote access only after a minimal Android probe APK or test runner exists, not after this local native foundation.

## What Works Locally

- Python unit tests run without Android hardware, AWS credentials, Qualcomm SDKs, or network access.
- A toy QPNPU model can be created, inspected, decoded with a CPU Python reference path, and emitted as benchmark JSON.
- Sample probe JSON can be validated and summarized.
- ADB raw-output fixtures validate the Phase 1 parser path without requiring a real device.
- Native CPU reference kernels can be built and tested with CMake on a machine with CMake and a C++17 compiler.
- Local CPU microbenchmarks can produce benchmark-schema JSON.
- The verifier clearly distinguishes PASS, FAIL, and BLOCKED native checks.
- Example kernel config can be validated and used to generate a tiny placeholder C++ file.

## What Is Stubbed

- The Phase 3 toy runtime is not a transformer and is not Qwen 9B inference.
- Android probe app is documentation only.
- Vulkan, NNAPI, and QNN backends are safe unavailable stubs.
- AWS Device Farm scripts only check for `aws`, print usage, and show intended commands.
- Generated kernels remain placeholders.
- No phone, accelerator, or NPU benchmark exists in Phase 3.

## Next Phases

1. Phase 4: Android probe app or native Android harness when device-side enumeration is needed.
2. Phase 5: Quantization validation with small model shards or fixtures.
3. Phase 6: Kernel generation and local native microbenchmarks beyond the reference kernels.
4. Phase 7: Android deployment and on-device microbenchmarks.
5. Phase 8: Backend probing for NNAPI, Vulkan, and QNN availability.
6. Phase 9: AWS Device Farm remote access and repeatable benchmark runs after a minimal Android runner exists.