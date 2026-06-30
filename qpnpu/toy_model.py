"""Create tiny deterministic Qwen-like smoke-test model artifacts."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from qpnpu.model_format import write_model_metadata


DEFAULT_TOY_CONFIG: dict[str, Any] = {
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
    "quantization": "none",
    "seed": 1234,
}

TOY_MODEL_WARNINGS = [
    "toy model only; not Qwen 9B",
    "local CPU Python reference only; not Android",
    "not NPU or QNN execution",
    "not a performance claim",
]


def create_toy_model(model_dir: Path, config: dict[str, Any] | None = None, overwrite: bool = False) -> dict[str, Any]:
    """Create a deterministic toy QPNPU model directory and return metadata."""

    model_dir = Path(model_dir)
    if model_dir.exists() and any(model_dir.iterdir()):
        if not overwrite:
            raise FileExistsError(f"refusing to overwrite existing model directory: {model_dir}")
        _remove_existing_model_dir(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    merged = dict(DEFAULT_TOY_CONFIG)
    if config:
        merged.update(config)
    _validate_config(merged)

    rng = np.random.default_rng(int(merged["seed"]))
    vocab_size = int(merged["vocab_size"])
    hidden_size = int(merged["hidden_size"])

    tensors = {
        "token_embedding.weight": rng.normal(0.0, 0.02, size=(vocab_size, hidden_size)).astype(np.float32),
        "norm.weight": np.linspace(0.98, 1.02, hidden_size, dtype=np.float32),
        "lm_head.weight": rng.normal(0.0, 0.02, size=(vocab_size, hidden_size)).astype(np.float32),
    }

    tensor_entries: list[dict[str, Any]] = []
    byte_offset = 0
    model_bin = model_dir / "model.bin"
    with model_bin.open("wb") as handle:
        for name, tensor in tensors.items():
            tensor_le = np.ascontiguousarray(tensor, dtype=np.dtype("<f4"))
            raw = tensor_le.tobytes(order="C")
            handle.write(raw)
            tensor_entries.append(
                {
                    "name": name,
                    "shape": list(tensor_le.shape),
                    "dtype": "fp32",
                    "quantization": "none",
                    "file": "model.bin",
                    "byte_offset": byte_offset,
                    "byte_length": len(raw),
                }
            )
            byte_offset += len(raw)

    metadata = {
        "schema_version": "0.1",
        "format": "qpnpu",
        "model": {key: merged[key] for key in DEFAULT_TOY_CONFIG if key != "seed"},
        "tensors": tensor_entries,
        "warnings": TOY_MODEL_WARNINGS,
        "notes": [
            "This smoke artifact validates local model-format plumbing only.",
            "It is intentionally too small and simple to represent Qwen 9B behavior.",
        ],
    }
    write_model_metadata(model_dir, metadata)
    _write_tokenizer_stub(model_dir)
    _write_readme(model_dir, metadata)
    return metadata


def _validate_config(config: dict[str, Any]) -> None:
    if config.get("architecture") != "qwen_toy":
        raise ValueError("toy model architecture must be qwen_toy")
    if config.get("dtype") != "fp32":
        raise ValueError("toy model only supports fp32")
    if config.get("quantization") != "none":
        raise ValueError("toy model creation only supports quantization=none")

    for key in [
        "hidden_size",
        "num_layers",
        "num_attention_heads",
        "num_key_value_heads",
        "intermediate_size",
        "vocab_size",
        "max_position_embeddings",
    ]:
        value = config.get(key)
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"{key} must be a positive integer")
    if config["vocab_size"] > 256:
        raise ValueError("ByteTokenizerStub supports vocab_size up to 256")
    if config["hidden_size"] % config["num_attention_heads"] != 0:
        raise ValueError("hidden_size must be divisible by num_attention_heads")
    if not isinstance(config.get("rope_theta"), (int, float)) or float(config["rope_theta"]) <= 0.0:
        raise ValueError("rope_theta must be positive")


def _remove_existing_model_dir(model_dir: Path) -> None:
    resolved = model_dir.resolve()
    cwd = Path.cwd().resolve()
    if resolved == cwd or resolved.parent == resolved:
        raise ValueError(f"refusing to overwrite unsafe model directory: {model_dir}")
    shutil.rmtree(model_dir)


def _write_tokenizer_stub(model_dir: Path) -> None:
    payload = {
        "schema_version": "0.1",
        "type": "byte_tokenizer_stub",
        "vocab_size": 256,
        "description": "Encodes UTF-8 bytes directly as token ids 0..255 and decodes bytes with replacement.",
        "warnings": [
            "This is not the Qwen tokenizer.",
            "It exists only for deterministic local smoke tests.",
        ],
    }
    (model_dir / "tokenizer_stub.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_readme(model_dir: Path, metadata: dict[str, Any]) -> None:
    model = metadata["model"]
    text = f"""# Toy Qwen Smoke Model

This directory contains a tiny deterministic QPNPU toy model for local smoke tests.

It is not Qwen 9B, not a transformer implementation, not an Android artifact, not NPU or QNN execution, and not a performance claim.

## Contents

- `metadata.json`: QPNPU toy metadata and tensor manifest.
- `model.bin`: fp32 tensor bytes for embedding, norm, and lm head.
- `tokenizer_stub.json`: byte-level tokenizer stub metadata.

## Model Summary

- architecture: {model['architecture']}
- hf_id: {model['hf_id']}
- hidden_size: {model['hidden_size']}
- num_layers: {model['num_layers']}
- vocab_size: {model['vocab_size']}
- dtype: {model['dtype']}
- quantization: {model['quantization']}
"""
    (model_dir / "README.md").write_text(text, encoding="utf-8")