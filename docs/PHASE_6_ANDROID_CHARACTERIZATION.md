# Phase 6 Android Characterization

Phase 6 extends the probe APK beyond basic device info and tiny native microbenchmarks. It adds a conservative on-device characterization ladder for CPU ISA evidence, thread scaling, memory bandwidth, quantization packing, and backend library load probes.

This phase still does not run Qwen 9B, QNN, NNAPI, Vulkan kernels, or NPU execution. It does not make a performance target claim.

## App Flow

Build the APK:

```powershell
cd android\probe-app
.\gradlew.bat assembleDebug
```

Upload/install the debug APK in AWS Device Farm Remote Access, launch `QPNPU Hardware Probe`, then tap:

- `Run Probe` for full Android hardware probe JSON.
- `Native Bench` for Phase 5 tiny native CPU benchmark JSON.
- `Characterize HW` for deeper characterization JSON.

The Phase 6 payload is logged between:

```text
QPNPU_PHASE6_JSON_BEGIN
QPNPU_PHASE6_JSON_END
```

It is also saved best-effort to:

```text
getExternalFilesDir(null)/phase6_characterization.json
```

## Extract Phase 6 JSON

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
## Payload Sections

- `cpu_isa`: `/proc/cpuinfo` plus `getauxval(AT_HWCAP/AT_HWCAP2)` evidence for ARM feature flags such as `i8mm`, `bf16`, `sve`, `sve2`, `svei8mm`, and `sme` when exposed by the NDK headers.
- `topology`: `std::thread::hardware_concurrency`, app-visible CPU affinity, and short thread-scaling loops.
- `memory`: bounded app-private copy-bandwidth fixtures over small buffers.
- `backend_load`: controlled `dlopen` checks for Vulkan, NNAPI, QNN, DSP RPC, and SNPE-like library names.
- `quantization`: tiny deterministic int4 packing/dequant fixture with explicit packing metadata.

## Interpretation

Use Phase 6 to decide the next safe gate:

- CPU ISA flags reported by both `/proc/cpuinfo` and auxv are stronger evidence than string hints alone.
- Thread and memory probes guide future CPU kernel tiling, but are short harness signals.
- `dlopen` success only proves a library can be loaded from the app process; it does not prove usable accelerator execution.
- Quantization fixture success validates packing/dequant plumbing only; it is not model accuracy.

The next recommended gates are guarded ARM instruction probes with SIGILL/process isolation, thread affinity/topology mapping, memory hierarchy probes, and backend API enumeration.

