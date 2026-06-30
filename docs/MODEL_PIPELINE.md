# Model Pipeline

The target model is a configurable Qwen-style 9B decoder model referred to as Qwen 3.5 9B for the trial. Phase 0 uses the placeholder Hugging Face id `Qwen/Qwen-placeholder-9B`.

Planned workflow:

1. Inspect Hugging Face-style `config.json` metadata.
2. Fetch model files into `models/` using explicit user action.
3. Convert metadata and tensor manifests into QPNPU format.
4. Quantize selected tensors with groupwise symmetric int4.
5. Validate quantized fixtures against a CPU reference backend.
6. Package model artifacts for Android deployment.

Phase 0 status:

- `scripts/model/fetch_model.py` prints an intended download command but does not download.
- `scripts/model/convert_to_qpnpu.py` prints a placeholder conversion plan.
- `scripts/model/quantize.py` can quantize a small `.npy` fixture, but it is not a full model quantizer.
- No model weights are stored in git.

