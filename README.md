# qwen-phone-npu-trial

Phase 0 repository skeleton for a future Snapdragon-class Android phone NPU trial with a configurable Qwen-style 9B decoder model.

The trial target is a Samsung Galaxy S26 Ultra-class Android phone with a Snapdragon-class SoC. The trial brief mentions "Snapdragon X Elite NPU", but actual CPU, GPU, NNAPI, QNN, and NPU capabilities must be detected at runtime before any backend is selected.

The long-term performance target is at least 20 decode tokens/sec. No performance has been measured in Phase 0.

## Current Status

This repository currently contains:

- Small Python helpers for config loading, schema validation, benchmark selection, kernel config hashing, model metadata validation, and lightweight int4 quantization.
- CLI stubs for model inspection, model fetch planning, placeholder conversion, quantization, kernel generation, probe summarization, and autotune dry runs.
- Documentation for the planned workflow, hardware probe, model pipeline, backends, benchmarking, AWS Device Farm, and performance targets.
- Native and Android placeholder directories only.

Phase 0 does not implement:

- Real Android APK logic.
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

## What Works Locally

- Unit tests run without Android hardware, AWS credentials, Qualcomm SDKs, or network access.
- Sample probe JSON can be validated and summarized.
- Example kernel config can be validated and used to generate a tiny placeholder C++ file.
- Autotune can print the planned future workflow in dry-run mode.
- Small NumPy arrays can be packed and quantized with Phase 0 int4 helpers.

## What Is Stubbed

- ADB scripts only check for `adb` and show intended actions.
- AWS Device Farm scripts only check for `aws`, print usage, and show intended commands.
- Native backends are documentation placeholders.
- Android probe app is documentation only.
- Kernel generation emits placeholder C++ and does not produce optimized kernels.

## Next Phases

1. Phase 1: ADB hardware probe and minimal Android probe runner.
2. Phase 2: Native CPU reference backend and benchmark harness.
3. Phase 3: Model metadata and conversion prototype using tiny fixtures.
4. Phase 4: Quantization validation with small model shards or fixtures.
5. Phase 5: Kernel generation and local native microbenchmarks.
6. Phase 6: Android deployment and on-device microbenchmarks.
7. Phase 7: Backend probing for NNAPI, Vulkan, and QNN availability.
8. Phase 8: AWS Device Farm remote access and repeatable benchmark runs.
9. Phase 9: Full model trial and performance analysis.

