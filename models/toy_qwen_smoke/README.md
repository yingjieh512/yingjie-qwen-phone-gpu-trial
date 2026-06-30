# Toy Qwen Smoke Model

This directory contains a tiny deterministic QPNPU toy model for local smoke tests.

It is not Qwen 9B, not a transformer implementation, not an Android artifact, not NPU or QNN execution, and not a performance claim.

## Contents

- `metadata.json`: QPNPU toy metadata and tensor manifest.
- `model.bin`: fp32 tensor bytes for embedding, norm, and lm head.
- `tokenizer_stub.json`: byte-level tokenizer stub metadata.

## Model Summary

- architecture: qwen_toy
- hf_id: local/toy-qwen-smoke
- hidden_size: 32
- num_layers: 1
- vocab_size: 256
- dtype: fp32
- quantization: none
