# Hardware Probe

The hardware probe detects actual Android device capabilities at runtime. It must not assume that a Samsung Galaxy S26 Ultra-class phone exposes any particular NPU backend.

## Phase 1 Status

Phase 1 implements a host-side ADB probe. It runs `adb shell` commands from the development machine, stores raw command output, and builds a schema-valid `probe_result.json`.

No Android APK is implemented yet. No NNAPI device enumeration, QNN execution, NPU execution, or performance microbenchmark is implemented.

## Run The Probe

With Android platform-tools installed and USB debugging enabled:

```bash
bash scripts/adb/collect_device_info.sh
```

Optional output directory:

```bash
bash scripts/adb/collect_device_info.sh --out benchmarks/results/my_probe
```

If multiple devices are connected, set `ANDROID_SERIAL` before running the script.

The default output directory is `benchmarks/results/<utc-timestamp>/`. The script also updates `benchmarks/results/latest_probe.json`.

## Files Created

Each probe result directory contains at least:

- `raw_getprop.txt`
- `raw_uname.txt`
- `raw_cpuinfo.txt`
- `raw_meminfo.txt`
- `raw_thermal.txt`
- `raw_sysfs_cpu.txt`
- `raw_gpu.txt`
- `raw_npu.txt`
- `probe_result.json`

Summarize the latest result with:

```bash
python tools/probe_parser/summarize_probe.py benchmarks/results/latest_probe.json
```

## Probe Fields

The structured JSON keeps the Phase 0 schema:

- `device`: manufacturer, model, Android version, ABI list, SoC hints, kernel string.
- `cpu`: processor count, features, hardware string, implementer/part hints, sysfs frequency and topology data when readable.
- `memory`: meminfo-derived totals and available memory.
- `gpu`: Vulkan, OpenCL, GLES, Adreno, and KGSL library hints.
- `npu`: QNN library hints, NNAPI hints, Hexagon DSP hints, HTP hints, and a conservative status.
- `thermal`: thermal zones and cooling devices when sysfs permits reads.
- `microbenchmarks`: a Phase 1 note only; no native microbenchmarks are run.
- `warnings`: missing files, inaccessible paths, and parse limitations.

## Known Limitations

- The script does not require root and does not bypass Android permissions.
- Sysfs paths may be restricted or absent on production devices.
- NNAPI device enumeration is not implemented until a native Android app or test runner exists.
- QNN detection is library-hint based only in Phase 1.
- GPU and NPU hints do not prove execution support.
- No performance microbenchmarks run in Phase 1.