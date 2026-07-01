# Phase 7A Guarded ARM ISA Probes

Phase 7A moves from reported CPU feature strings to small executable evidence. The Android probe APK now includes a guarded ISA probe action that runs tiny ARM64 instruction fixtures from the app process and emits structured JSON.

This phase is still conservative. It does not run Qwen 9B, does not execute QNN/NPU/NNAPI/Vulkan kernels, does not download models, and does not make a performance claim.

## Goal

Validate that selected app-reachable ARM CPU instructions can execute on the target when the feature is reported by `/proc/cpuinfo` or auxv. A failed or unsupported instruction should become JSON evidence, not an app crash.

## App Flow

Build the APK:

```powershell
cd android\probe-app
.\gradlew.bat assembleDebug
```

Upload/install the APK in AWS Device Farm Remote Access, launch `QPNPU Hardware Probe`, then tap:

```text
ISA Probe
```

The Phase 7A payload is logged between:

```text
QPNPU_PHASE7A_JSON_BEGIN
QPNPU_PHASE7A_JSON_END
```

It is also saved best-effort to:

```text
getExternalFilesDir(null)/phase7a_isa_probes.json
```

## Extract JSON

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind phase7a \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_phase7a_<date>.json
```

To preserve repeated button taps in one session:

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind all \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_probe_<date>.all_qpnpu_payloads.json
```

## Payload Sections

- `safety`: records the guard strategy. Phase 7A uses same-process `sigaction` plus `sigsetjmp`/`siglongjmp`; process isolation remains future work.
- `cpu_evidence`: records `/proc/cpuinfo` readability and auxv `AT_HWCAP` / `AT_HWCAP2` values.
- `isa_probes`: one object per candidate feature, including reported status, compiled status, guarded execution status, `sigill`, checksum, and notes.
- `summary`: counts total probes, successful executions, SIGILL catches, and skipped/deferred probes.

## Candidate Instructions

Phase 7A includes tiny fixtures for:

- ASIMD/NEON baseline add.
- CRC32 scalar instruction when reported.
- ASIMD dot-product `udot` when reported.
- I8MM `smmla` when reported.
- BF16 `bfdot` when reported.
- SVE vector-length query `rdvl` when reported.

SVE2, SVEI8MM, and SME are recorded as reported/deferred in this phase unless a later isolated probe is added. SME streaming-mode entry is intentionally not attempted here.

## Safety Rules

- Execute feature-specific instructions only when the feature is reported by `/proc/cpuinfo` or auxv.
- Wrap each instruction fixture with a SIGILL guard.
- Keep probes tiny and deterministic.
- Emit JSON for skipped, deferred, successful, or SIGILL outcomes.
- Treat same-process SIGILL handling as a practical smoke guard, not a complete fuzzer sandbox.

## Interpretation

An `executed_ok` result means one tiny instruction fixture ran from the Android app process. It does not prove generated-kernel correctness, useful throughput, Qwen inference, or accelerator availability.

A `sigill` result is useful too: it means reported feature evidence and executable behavior disagree, or the instruction fixture is not valid for the target/runtime. Future phases should use this to disable that code path until investigated.

The next gate after Phase 7A is generated/native CPU kernel correctness using only features that passed executable probes.