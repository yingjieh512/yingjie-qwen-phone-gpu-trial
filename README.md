# qwen-phone-npu-trial

Repository for a Snapdragon-class Android phone NPU trial with a configurable Qwen-style 9B decoder model.

The trial target is a Samsung Galaxy S26 Ultra-class Android phone with a Snapdragon-class SoC. The trial brief mentions "Snapdragon X Elite NPU", but actual CPU, GPU, NNAPI, QNN, and NPU capabilities must be detected at runtime before any backend is selected.

The long-term performance target is at least 20 decode tokens/sec. No performance has been measured yet.

## Current Status

Phase 1 adds a real host-side ADB hardware probe workflow. It collects best-effort raw Android system information with `adb shell`, writes a structured `probe_result.json`, and updates `benchmarks/results/latest_probe.json`.

This repository currently contains:

- Python helpers for config loading, schema validation, benchmark selection, kernel config hashing, model metadata validation, lightweight int4 quantization, and ADB probe parsing.
- CLI tools for probe summarization, probe JSON generation, model planning, placeholder kernel generation, and autotune dry runs.
- A host-side ADB collection script that requires `adb` and a connected debugging-enabled Android device only when you run it.
- Documentation for the planned workflow, hardware probe, model pipeline, backends, benchmarking, AWS Device Farm, and performance targets.
- Native and Android placeholder directories only.

This phase does not implement:

- Android APK logic.
- Real inference execution.
- Real AWS Device Farm runs.
- Real Qualcomm QNN integration.
- Real NPU execution.
- Model downloads.
- Performance claims.

## Quickstart

From the repository root:

```bash
python -m pytest tests
python tools/probe_parser/summarize_probe.py benchmarks/results/sample_probe.json
python tools/kernelgen/generate_kernels.py --probe benchmarks/results/sample_probe.json --config configs/kernel_config.example.json --out native/kernels/generated
python scripts/autotune/run_autotune.py --dry-run
```

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

## What Works Locally

- Unit tests run without Android hardware, AWS credentials, Qualcomm SDKs, or network access.
- Sample probe JSON can be validated and summarized.
- ADB raw-output fixtures validate the Phase 1 parser path without requiring a real device.
- Example kernel config can be validated and used to generate a tiny placeholder C++ file.
- Autotune can print the planned future workflow in dry-run mode.
- Small NumPy arrays can be packed and quantized with Phase 0 int4 helpers.

## What Is Stubbed

- Android probe app is documentation only.
- Native backends are documentation placeholders.
- AWS Device Farm scripts only check for `aws`, print usage, and show intended commands.
- Kernel generation emits placeholder C++ and does not produce optimized kernels.
- Benchmarks and microbenchmarks are not run in Phase 1.

## Next Phases

1. Phase 2: Native CPU reference backend and microbenchmark/probe foundation.
2. Phase 3: Model metadata and conversion prototype using tiny fixtures.
3. Phase 4: Android probe app or native Android harness when device-side enumeration is needed.
4. Phase 5: Quantization validation with small model shards or fixtures.
5. Phase 6: Kernel generation and local native microbenchmarks.
6. Phase 7: Android deployment and on-device microbenchmarks.
7. Phase 8: Backend probing for NNAPI, Vulkan, and QNN availability.
8. Phase 9: AWS Device Farm remote access and repeatable benchmark runs after a minimal Android runner exists.