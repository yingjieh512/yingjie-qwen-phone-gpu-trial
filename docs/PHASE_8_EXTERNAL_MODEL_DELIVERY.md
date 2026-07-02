# Phase 8 External Toy Model Delivery Demo

Phase 8 proves the missing real-world delivery shape: the APK can keep model weights out of the APK, fetch or copy a tiny external-style manifest, verify file hashes, cache files in app-private storage, and run the existing Android toy decode path from cached files.

This is a workable demo first. It is not Qwen 9B, not a Hugging Face credential flow, not QNN/NPU execution, and not a performance claim.

## What Was Added

- `qpnpu/model_artifact.py` validates small external QPNPU model manifests.
- `scripts/model/create_external_toy_artifact.py` creates a tiny sharded toy model artifact.
- `android/probe-app` has an `External Model` button.
- The APK includes `android.permission.INTERNET` for optional HTTPS manifest downloads.
- Blank manifest URL uses a bundled tiny manifest fallback, then caches the existing toy asset into app-private storage.
- Non-empty manifest URL downloads the manifest and relative/absolute file URLs over HTTP(S), verifies SHA-256, caches files, and runs toy decode from cached bytes.
- Phase 8 JSON is logged between `QPNPU_PHASE8_JSON_BEGIN` and `QPNPU_PHASE8_JSON_END`.
- `scripts/android/extract_probe_json_from_logcat.py --kind phase8` extracts and validates the result.

## Local Artifact Creation

Create a tiny external toy artifact:

```bash
python scripts/model/create_external_toy_artifact.py \
  --out models/external_toy_qwen_smoke \
  --hidden-size 16 \
  --overwrite
```

The artifact contains:

- `manifest.json`
- `metadata.json`
- `tokenizer_stub.json`
- `shards/model-00000.qpnpu`

The generated artifact is about 35 KB. It can be uploaded to S3, a static HTTPS server, GitHub raw content, or a Hugging Face dataset/repo. If hosted, update `manifest.json` URLs or regenerate it with `--base-url`.

Current hosted test manifest:

```text
https://huggingface.co/yingjieh512/toy-model-for-testing/resolve/main/external_toy_qwen_smoke/manifest.json
```

## Android Smoke Test

Build the APK:

```powershell
cd android\probe-app
.\gradlew.bat assembleDebug
```

In AWS Device Farm Remote Access:

1. Upload/install the debug APK.
2. Launch `QPNPU Hardware Probe`.
3. For the no-network fallback, leave the manifest URL blank.
4. For a hosted artifact, paste the HTTPS `manifest.json` URL.
5. Tap `External Model`.
6. Verify JSON appears in the UI and the app does not crash.
7. Download logcat and extract:

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind phase8 \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_phase8_<date>.json
```

## Expected JSON

The payload source is:

```text
android-phase8-external-model-demo
```

Important fields:

- `model_delivery.manifest_source`
- `model_delivery.cache_dir`
- `model_delivery.files[]`
- `model_delivery.all_sha256_verified: true`
- `toy_decode.generated_token_ids`
- `warnings`

## Guardrails

- The fallback path copies bundled toy assets into cache, so it proves cache/load/checksum plumbing but not internet delivery.
- The hosted URL path proves HTTPS manifest and shard download, but still only for tiny toy artifacts.
- Do not use this path for multi-GB Qwen weights yet.
- Do not claim NPU, QNN, NNAPI, Vulkan, or performance from Phase 8.
