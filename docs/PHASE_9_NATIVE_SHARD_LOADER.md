# Phase 9 Native Cached-Shard Loader

Phase 9 moves the external toy model path one step closer to a real model delivery architecture. Phase 8 proved that the Android app can download a tiny manifest-described artifact, cache it in app-private storage, verify SHA-256 checksums, and run a toy decode. Phase 9 reuses that verified cache but passes file paths into native code so JNI/C++ opens the metadata and shard files directly.

This phase is still a toy workflow. It is not Qwen 9B, not a Qwen tokenizer, not QNN/NPU/NNAPI/Vulkan execution, and not a performance claim.

## What It Validates

- Hosted manifest URL can be fetched on the Device Farm phone.
- Tiny model files are cached in app-private storage and checksum verified before use.
- Native JNI receives verified metadata and shard file paths rather than Java heap tensor bytes.
- Native code opens metadata from a file path and reads tensor shard bytes through a read-only mmap path.
- The existing native toy decode reference can consume the native-loaded bytes and emit deterministic JSON.
- Logcat extraction and validation support the Phase 9 marker pair.

## APK Smoke Flow

Build the debug APK:

```powershell
cd android\probe-app
.\gradlew.bat assembleDebug
```

Find the APK:

```bash
python scripts/android/find_probe_apk.py
```

In AWS Device Farm Remote Access:

1. Upload/install the rebuilt debug APK.
2. Launch `QPNPU Hardware Probe`.
3. Confirm the manifest URL field contains the hosted toy manifest, or paste:

   ```text
   https://huggingface.co/yingjieh512/toy-model-for-testing/resolve/main/external_toy_qwen_smoke/manifest.json
   ```

4. Tap `Shard Load`.
5. Verify the UI shows `source: android-phase9-native-shard-loader`.
6. Verify `native_model_loader.open_method` is `mmap_readonly`.
7. Verify `native_model_loader.java_tensor_bytes_passed` is `false`.
8. Verify `native_model_loader.all_sha256_verified_before_native_load` is `true`.
9. Stop the session and download logcat.

The app logs JSON between:

```text
QPNPU_PHASE9_JSON_BEGIN
QPNPU_PHASE9_JSON_END
```

Extract the payload:

```bash
python scripts/android/extract_probe_json_from_logcat.py   --kind phase9   --logcat path/to/devicefarm-logcat.txt   --out benchmarks/results/aws_remote_phase9_<date>.json
```

Preserve all QPNPU payloads from the same session:

```bash
python scripts/android/extract_probe_json_from_logcat.py   --kind all   --logcat path/to/devicefarm-logcat.txt   --out benchmarks/results/aws_remote_probe_<date>.all_qpnpu_payloads.json
```

## Expected JSON Signals

Key fields to check:

- `source`: `android-phase9-native-shard-loader`
- `backend`: `cpu_android_native_file_loader`
- `model_delivery.all_sha256_verified`: `true`
- `native_model_loader.loader_location`: `native_jni`
- `native_model_loader.open_method`: `mmap_readonly`
- `native_model_loader.tensor_shard_count`: at least `1`
- `native_model_loader.tensor_bytes`: greater than `0`
- `native_model_loader.java_tensor_bytes_passed`: `false`
- `generated_token_ids`: deterministic toy token IDs
- `warnings`: must state toy-only, not Qwen 9B, not NPU, and not a performance claim

## Known Limitations

- The tiny artifact is intentionally far smaller than any real Qwen model.
- Native code mmap-reads the shard files, then copies the mapped bytes into the existing toy reference buffer. That is acceptable for this phase because the purpose is proving native file ownership, not final zero-copy tensor execution.
- There is no safetensors reader, no Qwen tokenizer, no KV cache, no attention implementation, and no accelerator backend.
- Device Farm Remote Access remains manual. Automation should wait for a command-driven runner or instrumentation test.
