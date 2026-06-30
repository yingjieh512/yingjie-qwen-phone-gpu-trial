"""QPNPU model metadata and tensor helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


REQUIRED_TOP_LEVEL_KEYS = ["schema_version", "format", "model", "tensors"]
REQUIRED_MODEL_KEYS = [
    "architecture",
    "hf_id",
    "hidden_size",
    "num_layers",
    "num_attention_heads",
    "num_key_value_heads",
    "intermediate_size",
    "vocab_size",
    "max_position_embeddings",
    "rope_theta",
    "dtype",
    "quantization",
]
REQUIRED_TENSOR_KEYS = [
    "name",
    "shape",
    "dtype",
    "quantization",
    "file",
    "byte_offset",
    "byte_length",
]
_DTYPE_MAP = {"fp32": np.dtype("<f4")}


def minimal_model_metadata() -> dict[str, Any]:
    """Return a valid placeholder QPNPU model metadata object."""

    return {
        "schema_version": "0.1",
        "format": "qpnpu",
        "model": {
            "architecture": "qwen",
            "hf_id": "Qwen/Qwen-placeholder-9B",
            "hidden_size": 0,
            "num_layers": 0,
            "num_attention_heads": 0,
            "num_key_value_heads": 0,
            "intermediate_size": 0,
            "vocab_size": 0,
            "max_position_embeddings": 0,
            "rope_theta": 10000.0,
            "dtype": "fp32",
            "quantization": "none",
        },
        "tensors": [],
    }


def validate_model_metadata(data: dict[str, Any]) -> list[str]:
    """Validate QPNPU model metadata and return human-readable errors."""

    if not isinstance(data, dict):
        return ["model metadata must be a JSON object"]

    errors: list[str] = []
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in data:
            errors.append(f"missing required key: {key}")

    if "schema_version" in data and not isinstance(data["schema_version"], str):
        errors.append("schema_version must be a string")
    if "format" in data and data["format"] != "qpnpu":
        errors.append("format must be qpnpu")
    if "model" in data and not isinstance(data["model"], dict):
        errors.append("model must be an object")
    if "tensors" in data and not isinstance(data["tensors"], list):
        errors.append("tensors must be a list")

    model = data.get("model")
    if isinstance(model, dict):
        for key in REQUIRED_MODEL_KEYS:
            if key not in model:
                errors.append(f"missing required model key: {key}")
        for key in ["architecture", "hf_id", "dtype", "quantization"]:
            if key in model and not isinstance(model[key], str):
                errors.append(f"model.{key} must be a string")
        for key in [
            "hidden_size",
            "num_layers",
            "num_attention_heads",
            "num_key_value_heads",
            "intermediate_size",
            "vocab_size",
            "max_position_embeddings",
        ]:
            if key in model and (not isinstance(model[key], int) or model[key] < 0):
                errors.append(f"model.{key} must be a non-negative integer")
        if "rope_theta" in model and not isinstance(model["rope_theta"], (int, float)):
            errors.append("model.rope_theta must be numeric")

    tensors = data.get("tensors")
    if isinstance(tensors, list):
        seen_names: set[str] = set()
        for index, tensor in enumerate(tensors):
            prefix = f"tensors[{index}]"
            if not isinstance(tensor, dict):
                errors.append(f"{prefix} must be an object")
                continue
            for key in REQUIRED_TENSOR_KEYS:
                if key not in tensor:
                    errors.append(f"missing required tensor key: {prefix}.{key}")
            name = tensor.get("name")
            if "name" in tensor and not isinstance(name, str):
                errors.append(f"{prefix}.name must be a string")
            elif isinstance(name, str):
                if not name:
                    errors.append(f"{prefix}.name must not be empty")
                if name in seen_names:
                    errors.append(f"duplicate tensor name: {name}")
                seen_names.add(name)
            shape = tensor.get("shape")
            if "shape" in tensor:
                if not isinstance(shape, list):
                    errors.append(f"{prefix}.shape must be a list")
                else:
                    for dim_index, dim in enumerate(shape):
                        if not isinstance(dim, int) or dim < 0:
                            errors.append(f"{prefix}.shape[{dim_index}] must be a non-negative integer")
            for key in ["dtype", "quantization", "file"]:
                if key in tensor and not isinstance(tensor[key], str):
                    errors.append(f"{prefix}.{key} must be a string")
            for key in ["byte_offset", "byte_length"]:
                if key in tensor and (not isinstance(tensor[key], int) or tensor[key] < 0):
                    errors.append(f"{prefix}.{key} must be a non-negative integer")

    return errors


def write_model_metadata(path: str | Path, data: dict[str, Any]) -> Path:
    """Write ``metadata.json`` and return the file path used."""

    metadata_path = _metadata_path(path)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata_path


def read_model_metadata(path: str | Path) -> dict[str, Any]:
    """Read and return a QPNPU ``metadata.json`` object."""

    metadata_path = _metadata_path(path)
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {metadata_path}")
    return data


def tensor_index(metadata: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return tensor metadata keyed by tensor name."""

    tensors = metadata.get("tensors")
    if not isinstance(tensors, list):
        raise ValueError("metadata.tensors must be a list")

    index: dict[str, dict[str, Any]] = {}
    for tensor in tensors:
        if not isinstance(tensor, dict):
            raise ValueError("metadata.tensors entries must be objects")
        name = tensor.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("tensor entry is missing a non-empty name")
        if name in index:
            raise ValueError(f"duplicate tensor name: {name}")
        index[name] = tensor
    return index


def load_tensor(model_dir: str | Path, metadata: dict[str, Any], tensor_name: str) -> np.ndarray:
    """Load one fp32 tensor from a QPNPU model directory."""

    tensors = tensor_index(metadata)
    if tensor_name not in tensors:
        raise KeyError(f"tensor not found: {tensor_name}")

    entry = tensors[tensor_name]
    dtype_name = entry.get("dtype")
    if dtype_name not in _DTYPE_MAP:
        raise ValueError(f"unsupported tensor dtype for {tensor_name}: {dtype_name}")
    dtype = _DTYPE_MAP[dtype_name]

    shape = entry.get("shape")
    if not isinstance(shape, list) or not all(isinstance(dim, int) and dim >= 0 for dim in shape):
        raise ValueError(f"invalid shape for tensor {tensor_name}: {shape}")

    file_name = entry.get("file")
    byte_offset = entry.get("byte_offset")
    byte_length = entry.get("byte_length")
    if not isinstance(file_name, str) or not file_name:
        raise ValueError(f"invalid tensor file for {tensor_name}: {file_name}")
    if not isinstance(byte_offset, int) or byte_offset < 0:
        raise ValueError(f"invalid byte_offset for tensor {tensor_name}: {byte_offset}")
    if not isinstance(byte_length, int) or byte_length < 0:
        raise ValueError(f"invalid byte_length for tensor {tensor_name}: {byte_length}")

    expected_length = int(np.prod(shape, dtype=np.int64)) * dtype.itemsize
    if byte_length != expected_length:
        raise ValueError(
            f"tensor {tensor_name} byte_length mismatch: metadata has {byte_length}, expected {expected_length}"
        )

    tensor_path = Path(model_dir) / file_name
    with tensor_path.open("rb") as handle:
        handle.seek(byte_offset)
        raw = handle.read(byte_length)
    if len(raw) != byte_length:
        raise ValueError(f"tensor {tensor_name} is truncated in {tensor_path}")

    return np.frombuffer(raw, dtype=dtype).reshape(tuple(shape)).copy()


def _metadata_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.name == "metadata.json":
        return candidate
    if candidate.suffix == ".json":
        return candidate
    return candidate / "metadata.json"