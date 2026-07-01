# Phase 7C Generated Native Kernel Candidates

Phase 7C turns the Phase 7A ISA evidence into tiny generated native CPU kernel candidates inside the Android probe APK. It is the first generated-kernel ladder rung: candidates build with the APK, run through JNI, compare against deterministic references, and emit structured JSON for Device Farm extraction.

This phase is still conservative. It does not run Qwen 9B, does not use QNN/NPU/NNAPI/Vulkan execution, does not download models, and does not make a performance claim.

## Goal

Validate the generated-kernel harness before optimization work. A useful Phase 7C result answers:

- Did candidate generation produce native code that builds in the Android APK?
- Which reported CPU features were used for executed candidates?
- Did each executed candidate pass correctness against a deterministic reference?
- Were unsupported or experimental candidates skipped or deferred without crashing the app?
- Can Device Farm logcat extraction preserve the full candidate result set?

## App Flow

Build the APK:

```powershell
cd android\probe-app
.\gradlew.bat assembleDebug
```

Upload/install the APK in AWS Device Farm Remote Access, launch `QPNPU Hardware Probe`, then tap:

```text
Gen Kernels
```

The Phase 7C payload is logged between:

```text
QPNPU_PHASE7C_JSON_BEGIN
QPNPU_PHASE7C_JSON_END
```

It is also saved best-effort to:

```text
getExternalFilesDir(null)/phase7c_generated_kernels.json
```

## Extract JSON

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind phase7c \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_phase7c_<date>.json
```

To preserve all current ladder payloads from one session:

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind all \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_probe_<date>.all_qpnpu_payloads.json
```

## Candidate Set

Runnable candidates are tiny fixtures, selected from Phase 7A evidence where possible:

- `generated_scalar_fp32_matvec_v1`: portable scalar fp32 matvec baseline.
- `generated_asimd_fp32_matvec_4lane_v1`: ASIMD/NEON fp32 matvec candidate.
- `generated_asimddp_udot_tile_v1`: ASIMDDP `udot` tile candidate.
- `generated_i8mm_smmla_tile_v1`: I8MM `smmla` tile candidate.
- `generated_bf16_bfdot_tile_v1`: BF16 `bfdot` tile candidate.
- `generated_sve_vector_length_tile_selector_v1`: SVE vector-length query used to parameterize future kernels.

Experimental candidates are listed but not executed in same-process Phase 7C:

- `experimental_sve2_candidate_v1`
- `experimental_svei8mm_candidate_v1`
- `experimental_sme_candidate_v1`

These are intentionally deferred until a safer isolated process runner exists. SME streaming-mode entry is not attempted from the current app process.

## Payload Sections

- `generator`: static generator name, version, and kernel config hash.
- `safety`: SIGILL guard policy, feature-gating policy, and experimental deferral policy.
- `candidates`: per-candidate status, target feature, shape, correctness, checksum, optional benchmark object, warnings, and notes.
- `summary`: candidate counts, executed counts, correctness count, SIGILL count, skipped/deferred/experimental counts.
- `warnings`: clear non-performance and non-accelerator guardrails.

## Interpretation

A `passed_correctness` candidate means one tiny generated CPU fixture produced the expected result on the Android app process. It does not prove a production kernel, it does not prove useful throughput, and it does not prove Qwen inference.

A `skipped_feature_not_reported` candidate means the device did not report the required feature in `/proc/cpuinfo`, so the app did not execute that path.

A `deferred_no_safe_kernel` candidate means the feature is interesting but needs stricter isolation before execution. This is expected for SVE2, SVEI8MM, and SME in this phase.

A `sigill` result is useful evidence and should disable that candidate until investigated.

The next gate should either improve generated CPU candidates under this same JSON/test ladder or begin conservative backend API enumeration without making accelerator execution claims.