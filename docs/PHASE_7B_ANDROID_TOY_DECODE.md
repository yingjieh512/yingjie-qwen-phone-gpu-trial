# Phase 7B Android Toy Decode Asset Smoke

Phase 7B packages a tiny deterministic QPNPU toy model inside the Android probe APK and runs a native CPU/JNI reference decode from app assets. This is the first Android-side model workflow smoke path: asset loading, metadata/tensor parsing, byte-token prompt handling, native math, benchmark-schema JSON, UI display, logcat markers, and extraction.

This is not Qwen 9B. It does not use the Qwen tokenizer, QNN, NNAPI, Vulkan, or NPU execution. It is not a performance target measurement.

## Goal

Validate that the Android app can carry a very small model artifact and execute a deterministic decode-like loop locally on the device CPU. This de-risks APK asset packaging, JNI boundaries, binary tensor loading, JSON output, and Device Farm artifact extraction before attempting any real model or accelerator backend.

## App Flow

Build the APK:

```powershell
cd android\probe-app
.\gradlew.bat assembleDebug
```

Upload/install the APK in AWS Device Farm Remote Access, launch `QPNPU Hardware Probe`, then tap:

```text
Toy Decode
```

The Phase 7B payload is logged between:

```text
QPNPU_TOY_DECODE_JSON_BEGIN
QPNPU_TOY_DECODE_JSON_END
```

It is also saved best-effort to:

```text
getExternalFilesDir(null)/toy_decode.json
```

## Extract JSON

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind toy_decode \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_toy_decode_<date>.json
```

To preserve repeated button taps in one session:

```bash
python scripts/android/extract_probe_json_from_logcat.py \
  --kind all \
  --logcat path/to/devicefarm-logcat.txt \
  --out benchmarks/results/aws_remote_probe_<date>.all_qpnpu_payloads.json
```

## Packaged Toy Model

The APK contains:

```text
app/src/main/assets/toy_qwen_7b/metadata.json
app/src/main/assets/toy_qwen_7b/model.bin
app/src/main/assets/toy_qwen_7b/tokenizer_stub.json
app/src/main/assets/toy_qwen_7b/README.md
```

The asset model is generated from the Phase 3 toy model path with `hidden_size=16`, `vocab_size=256`, and a fixed seed. The tensor file is intentionally tiny.

## Native Decode Loop

For prompt `hello` and `max_new_tokens=8`, the native path:

1. Loads QPNPU metadata and `model.bin` from assets.
2. Encodes the prompt with a byte-tokenizer stub.
3. Looks up the current token embedding.
4. Applies RMSNorm with the toy `norm.weight`.
5. Computes logits with the toy `lm_head.weight`.
6. Selects the next token by deterministic argmax.
7. Feeds the generated token back into the next step.
8. Emits decode and embedded benchmark JSON.

## Validation

Host-side validation lives in:

```text
qpnpu/android_toy_decode.py
tests/test_android_toy_decode.py
tests/fixtures/android_toy_decode_logcat_smoke.txt
```

The validator checks required fields, tokenizer stub disclosure, generated length, embedded benchmark schema, and warnings that this is not Qwen 9B, not NPU execution, and not a performance claim.

## Interpretation

A successful Phase 7B run means the Android APK can load a tiny local model asset and run a deterministic native CPU reference decode-like loop. It does not mean real Qwen inference works, it does not prove accelerator availability, and the reported local CPU toy throughput must not be compared to the 20 tokens/sec target.

The next gate should move from toy decode plumbing toward generated CPU kernel candidates or backend capability selection while preserving the same strict JSON/test ladder.