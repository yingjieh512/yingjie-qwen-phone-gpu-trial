# Phase 10 Toy Layer Slice

This directory contains a tiny deterministic QPNPU one-layer slice artifact.

It validates reference math and tensor format plumbing for embedding, RMSNorm, linear projections, RoPE, causal softmax attention, MLP, and final logits. It is not Qwen 9B, not a complete transformer runtime, not Android execution, not NPU or QNN execution, and not a performance claim.

## Contents

- `metadata.json`: QPNPU tensor metadata.
- `model.bin`: fp32 tensor bytes for the tiny slice.
- `reference_outputs.json`: deterministic expected intermediate outputs.
- `tokenizer_stub.json`: byte-level tokenizer stub metadata.

## Model Summary

- architecture: qwen_toy_layer_slice
- hf_id: local/qwen-toy-layer-slice-smoke
- hidden_size: 32
- num_layers: 1
- num_attention_heads: 4
- intermediate_size: 64
- vocab_size: 256
