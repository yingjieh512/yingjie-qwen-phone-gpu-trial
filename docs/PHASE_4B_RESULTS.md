# Phase 4B Results

Phase 4B turns the first AWS Device Farm Remote Access smoke session into durable project artifacts.

## Inputs

- Probe artifact: `benchmarks/results/aws_remote_probe_2026-07-01.json`
- Summary artifact: `benchmarks/results/aws_remote_probe_2026-07-01.summary.json`
- Hardware profile: `docs/TARGET_HARDWARE_PROFILE.md`
- Neutral hardware characterization: `benchmarks/results/aws_remote_probe_2026-07-01.hw_model.json`
- Characterization report: `docs/HARDWARE_CHARACTERIZATION.md`

## What Worked

- The Android probe APK installed and ran on AWS Device Farm Remote Access.
- The app emitted JSON to logcat between `QPNPU_PROBE_JSON_BEGIN` and `QPNPU_PROBE_JSON_END`.
- The extracted JSON validates with the common probe shape.
- The target phone reports Samsung model `SM-S948U1`, Android 16, SDK 36, `arm64-v8a`, and QTI `SM8850`.
- CPU and memory files were readable from app context.
- GPU/OpenCL/GLES/Adreno hints were visible.
- CDSP/HTP/SNPE-adjacent hints were visible.
- Thermal/cooling entries were readable, including CPU, GPU, KGSL, CDSP, DDR, and UFS-related zones.


## Relation To Ignition-Style Hardware Characterization

The Phase 4B probe is now more than device-info collection. It produces an execution-model-neutral hardware model with:

- target identity and Android runtime access evidence
- reachable execution units with confidence levels
- CPU feature evidence from `/proc/cpuinfo`
- GPU and NPU/DSP hint units without overclaiming execution
- memory and thermal telemetry context
- explicit probe gaps
- a structured fuzzing/test-gate plan for the next native Android phase

This is still not a real ISA fuzzer run. Safe instruction probing requires the Phase 5 JNI/NDK harness so each candidate instruction can be isolated and handled without crashing the app process.

## What This Does Not Prove

- It does not prove QNN runtime availability.
- It does not prove NPU execution.
- It does not prove Vulkan execution.
- It does not run Qwen 9B.
- It does not benchmark decode speed.
- It does not support any performance claim.

## Engineering Interpretation

- CPU fallback remains mandatory.
- The phone exposes useful Qualcomm/CDSP/Adreno hints, so later backend probes are worth doing.
- Direct QNN access remains unknown because the first probe did not find `libQnn*.so` names.
- The next probe APK should include direct known-library checks and a compact summary object.
- The next implementation phase should be an Android native microbenchmark harness, not full Qwen deployment.

## Recommended Next Phase

Phase 5 should add a Java/JNI/NDK path that runs small native CPU kernels on Android and emits benchmark JSON. That gives us repeatable on-device timing and packaging before any large model or NPU work.

## Useful Commands

Extract clean JSON from downloaded or pasted logcat text:

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --logcat path/to/logcat.txt \
  --out benchmarks/results/aws_remote_probe_<date>.json
```

Summarize a saved Android probe JSON file:

```bash
python scripts/android/summarize_probe_json.py \
  --input benchmarks/results/aws_remote_probe_2026-07-01.json \
  --out-json benchmarks/results/aws_remote_probe_2026-07-01.summary.json \
  --out-md docs/TARGET_HARDWARE_PROFILE.md
```
Build the execution-model-neutral hardware model:

```bash
python scripts/android/characterize_hardware.py \
  --input benchmarks/results/aws_remote_probe_2026-07-01.json \
  --out-json benchmarks/results/aws_remote_probe_2026-07-01.hw_model.json \
  --out-md docs/HARDWARE_CHARACTERIZATION.md
```