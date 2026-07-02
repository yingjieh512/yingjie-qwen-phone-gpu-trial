# Phase 10 Layer-Slice Correctness Ladder

Phase 10 creates the first deterministic Qwen-like layer-slice artifact. It is still deliberately tiny, but it exercises the operator sequence needed before a real model path can be trusted:

- byte-token embedding
- RMSNorm
- Q/K/V and output linear projections
- RoPE
- causal attention scores
- softmax
- attention context
- post-attention residual
- MLP gate/up/down path
- final logits and next-token argmax

This phase is a correctness ladder only. It is not Qwen 9B, not a Qwen tokenizer, not Android execution, not QNN/NPU/NNAPI/Vulkan execution, and not a performance claim.

## Local Smoke Flow

Create the tiny artifact:

```bash
python scripts/model/create_layer_slice.py --out models/layer_slice_smoke --overwrite
```

Run the correctness ladder:

```bash
python scripts/model/run_layer_slice_check.py \
  --model-dir models/layer_slice_smoke \
  --out benchmarks/results/layer_slice_smoke.json
```

Expected result:

- `metadata.json` validates with the QPNPU model metadata helper.
- `model.bin` contains small fp32 tensors only.
- `reference_outputs.json` stores deterministic expected checkpoints.
- `layer_slice_smoke.json` reports `summary.all_passed: true`.
- The output warnings say this is not Qwen 9B, not NPU execution, and not a performance claim.

## Artifact Contents

- `metadata.json`: QPNPU tensor metadata for the tiny slice.
- `model.bin`: fp32 tensor data.
- `reference_outputs.json`: expected intermediate tensors and checksums.
- `tokenizer_stub.json`: byte-level tokenizer stub metadata.
- `README.md`: artifact-local explanation and guardrails.

## Why This Matters

The full trial target cannot jump from toy token generation directly to a 9B throughput number. First, each model-stage operation must be reproducible against known reference values. Phase 10 gives us a small, deterministic set of tensors and intermediate outputs that can later be ported into Android native code and compared stage by stage.

The next Android step should load this same layer-slice artifact through the Phase 9 native cached-shard path and compare native outputs against `reference_outputs.json`.

## Still Missing Before Full Qwen 9B

- Real Qwen tokenizer.
- Real Qwen 3.5 9B config and tensor naming.
- Safetensors or other real checkpoint conversion.
- Quantized weight formats for the target backend.
- KV cache and decode loop over real layers.
- Android native layer-slice runner.
- Backend API enumeration for NNAPI/Vulkan/QNN.
- Any accelerator-backed subgraph.
- Large external model delivery and storage plan.
- Thermal-aware benchmark automation.
