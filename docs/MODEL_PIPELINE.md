# Model Pipeline

The target model for the long-term trial is a configurable Qwen-style 9B decoder model. No Qwen 9B weights are downloaded, stored, converted, or executed in Phase 3.

## Phase 3 Local Toy Workflow

Phase 3 introduces a tiny deterministic QPNPU artifact for local workflow validation:

```bash
python scripts/model/create_toy_qwen.py --out models/toy_qwen_smoke --overwrite
python scripts/model/inspect_model.py --model-dir models/toy_qwen_smoke
python scripts/model/run_toy_decode.py \
  --model-dir models/toy_qwen_smoke \
  --prompt "hello" \
  --max-new-tokens 8 \
  --out benchmarks/results/toy_decode_smoke.json
```

This toy model is not a real transformer, not Qwen 9B, not the Qwen tokenizer, not Android execution, not NPU/QNN execution, and not a performance claim. It exists to validate the local model-format, tensor-loading, CPU-reference math, CLI, and benchmark-output path.

## QPNPU Toy Model Format

A toy QPNPU model directory contains:

- `metadata.json`: schema, model config, tensor manifest, and warnings.
- `model.bin`: small fp32 tensor data.
- `tokenizer_stub.json`: byte-level tokenizer stub metadata.
- `README.md`: local artifact explanation and non-claim warnings.

`metadata.json` uses schema version `0.1`:

```json
{
  "schema_version": "0.1",
  "format": "qpnpu",
  "model": {
    "architecture": "qwen_toy",
    "hf_id": "local/toy-qwen-smoke",
    "hidden_size": 32,
    "num_layers": 1,
    "num_attention_heads": 4,
    "num_key_value_heads": 4,
    "intermediate_size": 64,
    "vocab_size": 256,
    "max_position_embeddings": 128,
    "rope_theta": 10000.0,
    "dtype": "fp32",
    "quantization": "none"
  },
  "tensors": [
    {
      "name": "token_embedding.weight",
      "shape": [256, 32],
      "dtype": "fp32",
      "quantization": "none",
      "file": "model.bin",
      "byte_offset": 0,
      "byte_length": 32768
    }
  ]
}
```

Tensor entries may point to byte offsets inside binary files. Phase 3 supports loading fp32 tensors for the toy workflow.

## Toy Decode Flow

The CPU Python reference runtime performs this deterministic loop for each generated token:

1. Encode the prompt with the byte tokenizer stub.
2. Read the current token embedding.
3. Apply RMSNorm with `norm.weight`.
4. Compute `lm_head.weight @ hidden`.
5. Add a deterministic token/position bias so the smoke decode does not collapse to a single constant token.
6. Select the next token with argmax and feed it back.

No sampling, attention cache, transformer block, RoPE attention, Qwen tokenizer, Android backend, or NPU backend is implemented here.

## Small Fixture Conversion

`scripts/model/convert_to_qpnpu.py` can convert one small local `.npy` tensor into a one-tensor QPNPU fixture:

```bash
python scripts/model/convert_to_qpnpu.py \
  --input-npy path/to/tensor.npy \
  --tensor-name fixture.weight \
  --output-dir models/fixture.qpnpu
```

This is not full safetensors conversion. Full Qwen model conversion remains future work.

## Future Full-Model Workflow

Planned later-phase workflow:

1. Inspect Hugging Face-style `config.json` metadata.
2. Fetch model files into `models/` using explicit user action.
3. Convert metadata and tensor manifests into QPNPU format.
4. Quantize selected tensors with groupwise symmetric int4.
5. Validate quantized fixtures against a CPU reference backend.
6. Package model artifacts for Android deployment.

No model weights are stored in git.

## Phase 10 Layer-Slice Artifact

Phase 10 adds a tiny deterministic Qwen-like one-layer slice. It uses QPNPU `metadata.json` plus a small fp32 `model.bin` and `reference_outputs.json` checkpoints for embedding, RMSNorm, linear projections, RoPE, causal softmax attention, MLP, final logits, and next-token argmax.

Create and check it locally:

```bash
python scripts/model/create_layer_slice.py --out models/layer_slice_smoke --overwrite
python scripts/model/run_layer_slice_check.py --model-dir models/layer_slice_smoke --out benchmarks/results/layer_slice_smoke.json
```

This is a correctness artifact only. It is not a full Qwen checkpoint conversion, not Android execution, not NPU execution, and not a performance result.
