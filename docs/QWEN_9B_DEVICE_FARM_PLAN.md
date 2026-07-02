# Qwen 9B Device Farm Delivery Plan

This plan explains how to move from the current probe APK to real Qwen-style model testing on an AWS Device Farm phone without embedding a multi-GB model in the APK.

## Core Constraint

The APK must stay small. A real 9B model should not be packaged directly into the Android application:

- Raw fp16 9B weights are roughly 18 GB before tokenizer, metadata, runtime buffers, and KV cache.
- Int8 weights are roughly 9 GB before overhead.
- Int4 weights are roughly 4.5 GB before scales, tensor metadata, padding, and KV cache.
- The current Device Farm upload path shows a 4 GB APK limit, and large embedded assets would also slow every build/install cycle.

The APK should contain only:

- The Java UI and JNI runtime.
- Native CPU fallback kernels and generated candidate kernels.
- Backend probes and loader code.
- A small bootstrap config or a user-provided manifest URL.

Model weights should be delivered at runtime as external, sharded, checksum-verified artifacts.

## Recommended Model Artifact Shape

Create an offline QPNPU model package before the phone ever sees it:

```text
qwen_qpnpu_int4/
  manifest.json
  tokenizer.json
  metadata.json
  shards/
    shard_00000.qpnpu
    shard_00001.qpnpu
    ...
```

The manifest should include:

- `schema_version`
- `model_id`
- `architecture`
- `quantization`
- `tensor_count`
- `total_bytes`
- `shards`: URL or object key, byte length, SHA-256, tensor ranges
- tokenizer metadata
- warnings that the artifact is not bundled in the APK

Do conversion and quantization offline on a workstation or cloud instance. Do not require Hugging Face credentials on the phone.

## Runtime Delivery Strategy

Preferred path:

1. Upload the converted shards to S3 or another HTTPS object store.
2. Generate short-lived, read-only presigned URLs for the manifest and shards.
3. Paste or provide the manifest URL to the APK during a test session.
4. The APK downloads shards into app-private storage, such as `getExternalFilesDir(null)/models/<model_id>/`.
5. The APK verifies SHA-256 for every shard before loading.
6. The loader uses mmap or streaming reads instead of copying the full model into Java heap.

Security rules:

- Do not place AWS access keys in the APK.
- Do not place Hugging Face credentials in the APK.
- Do not enter long-lived secrets into Device Farm Remote Access.
- Use short-lived URLs and delete cached artifacts when they are no longer needed.

Reliability rules:

- Check free storage before downloading.
- Use resumable range downloads.
- Keep a local manifest state file so interrupted sessions can continue.
- Validate every shard hash.
- Start with tiny fake shards, then a small model, then a one-layer slice, then the full quantized artifact.

## Device Farm Role

AWS Device Farm Remote Access is useful for manual smoke validation:

- APK installs.
- UI works.
- Logs and JSON extraction work.
- Tiny native kernels run.
- Small artifact download and hash verification work.

It is not ideal as the primary environment for repeated multi-GB model iteration because sessions are time-limited, storage may not persist, and long downloads make feedback slow. For heavy full-model iteration, prefer a physical phone or a persistent rented phone when possible. Use Device Farm for checkpoint validation and final smoke/regression runs.

Automated Device Farm runs should come later, after the APK has a non-interactive test runner that can download a small manifest, run a bounded test, and emit logs/artifacts without manual tapping.

## Rest Phase Plan

### Phase 8A: External Artifact Manifest

Exit criteria:

- Define a QPNPU sharded model manifest schema.
- Generate tiny fake model shards locally.
- Validate manifest fields, byte sizes, SHA-256, and shard ordering with Python tests.
- No Android download, real Qwen, Hugging Face credentials, or network access is required.

### Phase 8B: Android Downloader And Cache

Exit criteria:

- APK accepts a manifest URL or bundled test manifest.
- APK downloads tiny test shards into app-private storage.
- Resume, SHA-256 verification, free-space checks, and clear error JSON work.
- Logs include manifest/download/cache JSON markers.
- Device Farm validates only tiny shards first.

### Phase 9: Android Sharded Loader

Exit criteria:

- Native loader opens verified shards from app-private storage.
- Loader can mmap or stream selected tensor ranges.
- Tiny external toy model loads from downloaded shards instead of APK assets.
- Tokenizer and metadata paths remain deterministic.

### Phase 10: Layer-Slice Correctness Ladder

Exit criteria:

- Offline tools export one tiny Qwen-like layer slice in QPNPU format.
- Android CPU reference runs embedding, RMSNorm, matvec/linear, RoPE, softmax, and MLP slice checks.
- Each op and layer slice compares against Python reference values.
- No speed claim is made.

### Phase 11: Quantized Operator Expansion

Exit criteria:

- Add int4/int8 tensor block formats matching the offline converter.
- Add generated CPU kernels for the exact matmul and dequant shapes needed by the model.
- Validate every operator against Python reference fixtures.
- Keep CPU fallback mandatory.

### Phase 12: Backend API Enumeration

Exit criteria:

- Enumerate Vulkan and NNAPI capabilities through real APIs, not just `dlopen`.
- Attempt QNN only if a legally usable Qualcomm SDK/runtime path is available.
- Record capability JSON and conservative backend selection.
- Do not claim NPU execution from string hints.

### Phase 13: First Accelerator-Backed Subgraph

Exit criteria:

- Run one tiny supported op or subgraph through Vulkan, NNAPI, or QNN if available.
- Compare output against CPU reference.
- Fall back to CPU for unsupported ops.
- Record backend, shape, correctness, and thermal context.

### Phase 14: Progressive Model Scale-Up

Exit criteria:

- Run external artifact checks in this order: tiny fake shards, toy model, one-layer slice, small real model, larger real model, then quantized 9B.
- For 9B, first prove load and one-token decode correctness before throughput work.
- Capture memory, storage, thermal, and failure modes at every scale.

### Phase 15: Automated Device Farm Regression

Exit criteria:

- Replace manual tapping with an instrumentation or command-driven test runner.
- Upload APK, run bounded tests, retrieve logs/artifacts, and validate JSON automatically.
- Keep large model tests optional and externally configured.

### Phase 16: Performance Optimization Gate

Exit criteria:

- Only after correctness passes, measure decode throughput with fixed prompts, model artifact hash, backend config hash, thermal state, and repeated runs.
- Report whether `>=20` decode tokens/sec is achieved only if the full real model path produced reproducible benchmark artifacts.

## Current Guardrail

The current APK proves hardware characterization, native CPU harnessing, toy decode plumbing, guarded ISA probes, and generated CPU candidate correctness. It still does not run Qwen 9B and still does not execute on the NPU.
