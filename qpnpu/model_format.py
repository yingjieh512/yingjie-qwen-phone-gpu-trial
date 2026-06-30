"""QPNPU model metadata helpers."""

from __future__ import annotations

from typing import Any


REQUIRED_TOP_LEVEL_KEYS = ["schema_version", "format", "model", "tensors"]
REQUIRED_MODEL_KEYS = [
    "architecture",
    "hf_id",
    "hidden_size",
    "num_layers",
    "num_attention_heads",
    "num_key_value_heads",
    "vocab_size",
]


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
            "vocab_size": 0,
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
        for key in ["architecture", "hf_id"]:
            if key in model and not isinstance(model[key], str):
                errors.append(f"model.{key} must be a string")
        for key in [
            "hidden_size",
            "num_layers",
            "num_attention_heads",
            "num_key_value_heads",
            "vocab_size",
        ]:
            if key in model and (not isinstance(model[key], int) or model[key] < 0):
                errors.append(f"model.{key} must be a non-negative integer")

    return errors

