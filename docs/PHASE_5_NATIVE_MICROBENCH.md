# Phase 5 Native Microbenchmark Harness

Phase 5 adds a tiny Android NDK/JNI harness to the existing `QPNPU Probe` APK. It runs deterministic CPU-only native fixtures on the phone and emits benchmark-schema JSON to the UI, logcat, and app-private external storage.

This is not Qwen 9B inference, not QNN, not NPU execution, and not a performance target claim.

## What Runs

The native library is built as `qpnpu_probe_native` for `arm64-v8a` and currently includes:

- `fp32_matvec`: 16x32 matrix-vector reference fixture.
- `int4_dequant_matvec`: 16x32 signed int4 unpack/dequant plus matvec fixture.
- `rmsnorm`: 64-element RMSNorm fixture.
- `softmax`: 64-element stable softmax fixture.
- `rope`: 64-element RoPE rotation fixture.

Each fixture uses deterministic inputs, checks native output against an internal reference, and reports `correctness_passed` and `max_abs_error`.

## Build

```powershell
cd android\probe-app
.\gradlew.bat assembleDebug
```

Or on macOS/Linux:

```bash
cd android/probe-app
./gradlew assembleDebug
```

Find the APK:

```bash
python scripts/android/find_probe_apk.py
```

Expected debug APK path:

```text
android/probe-app/app/build/outputs/apk/debug/app-debug.apk
```

## Manual Device Farm Flow

1. Start an AWS Device Farm Remote Access Android session.
2. Upload/install the debug APK.
3. Launch `QPNPU Probe`.
4. Tap `Run Probe` for the full hardware probe with an embedded `microbenchmarks` object.
5. Tap `Native Bench` for the standalone native benchmark payload.
6. Verify the UI shows JSON and the app does not crash.
7. Retrieve logcat from the session if available.

The standalone native benchmark logcat markers are:

```text
QPNPU_NATIVE_BENCH_JSON_BEGIN
...
QPNPU_NATIVE_BENCH_JSON_END
```

The full probe markers remain:

```text
QPNPU_PROBE_JSON_BEGIN
...
QPNPU_PROBE_JSON_END
```

## Extract Native Benchmark JSON From Logcat

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind native \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_native_microbench_<date>.json
```

Extract the full hardware probe JSON with the default mode:

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_probe_<date>.json
```

## Interpretation

Use Phase 5 results to confirm:

- APK packaging includes native `arm64-v8a` code.
- JNI calls work on the target device.
- Basic native timing works.
- Small CPU reference kernels execute and return structured JSON.
- Results can be retrieved from UI/logcat/files.

Do not use Phase 5 numbers to claim Qwen throughput or NPU performance. The fixtures are intentionally tiny, CPU-only, and designed to validate the execution harness.
