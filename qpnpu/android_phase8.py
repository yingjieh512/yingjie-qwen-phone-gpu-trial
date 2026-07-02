"""Validation helpers for Android Phase 8 external model delivery payloads."""

from __future__ import annotations

from typing import Any

from qpnpu.android_toy_decode import validate_android_toy_decode


REQUIRED_PHASE8_KEYS = [
    "schema_version",
    "source",
    "backend",
    "model",
    "model_delivery",
    "toy_decode",
    "generated_token_ids",
    "warnings",
]


def validate_phase8_external_model(data: dict[str, Any]) -> list[str]:
    """Validate a Phase 8 Android external model delivery payload."""

    if not isinstance(data, dict):
        return ["Phase 8 payload must be a JSON object"]

    errors: list[str] = []
    for key in REQUIRED_PHASE8_KEYS:
        if key not in data:
            errors.append(f"missing required key: {key}")

    if data.get("source") != "android-phase8-external-model-demo":
        errors.append("source must be android-phase8-external-model-demo")
    if data.get("backend") != "cpu_android_native_reference":
        errors.append("backend must be cpu_android_native_reference")

    model = data.get("model")
    if not isinstance(model, dict):
        errors.append("model must be an object")
    else:
        if model.get("architecture") != "qwen_toy":
            errors.append("model.architecture must be qwen_toy")
        for key in ["hidden_size", "num_layers", "vocab_size"]:
            if not isinstance(model.get(key), int) or model.get(key) <= 0:
                errors.append(f"model.{key} must be a positive integer")

    delivery = data.get("model_delivery")
    if not isinstance(delivery, dict):
        errors.append("model_delivery must be an object")
    else:
        for key in ["manifest_source", "cache_dir"]:
            if not isinstance(delivery.get(key), str) or not delivery.get(key):
                errors.append(f"model_delivery.{key} must be a non-empty string")
        if delivery.get("all_sha256_verified") is not True:
            errors.append("model_delivery.all_sha256_verified must be true")
        files = delivery.get("files")
        if not isinstance(files, list) or not files:
            errors.append("model_delivery.files must be a non-empty list")
        else:
            for index, entry in enumerate(files):
                errors.extend(_validate_delivery_file(entry, index))

    toy_decode = data.get("toy_decode")
    if not isinstance(toy_decode, dict):
        errors.append("toy_decode must be an object")
    else:
        errors.extend(f"toy_decode: {error}" for error in validate_android_toy_decode(toy_decode))

    generated = data.get("generated_token_ids")
    if not isinstance(generated, list):
        errors.append("generated_token_ids must be a list")
    elif isinstance(toy_decode, dict) and isinstance(toy_decode.get("generated_token_ids"), list):
        if generated != toy_decode["generated_token_ids"]:
            errors.append("generated_token_ids must match toy_decode.generated_token_ids")

    warnings = data.get("warnings")
    if isinstance(warnings, list):
        joined = " ".join(str(item).lower() for item in warnings)
        for required in ["external", "toy", "not qwen 9b", "not npu", "not a performance"]:
            if required not in joined:
                errors.append(f"warnings must mention {required}")
    elif "warnings" in data:
        errors.append("warnings must be a list")

    return errors


def _validate_delivery_file(entry: Any, index: int) -> list[str]:
    errors: list[str] = []
    prefix = f"model_delivery.files[{index}]"
    if not isinstance(entry, dict):
        return [f"{prefix} must be an object"]
    for key in ["role", "path", "byte_length", "sha256", "cache_path"]:
        if key not in entry:
            errors.append(f"{prefix}: missing required key: {key}")
    for key in ["role", "path", "sha256", "cache_path"]:
        if key in entry and (not isinstance(entry[key], str) or not entry[key]):
            errors.append(f"{prefix}.{key} must be a non-empty string")
    if not isinstance(entry.get("byte_length"), int) or entry.get("byte_length") <= 0:
        errors.append(f"{prefix}.byte_length must be a positive integer")
    if entry.get("verified") is not True:
        errors.append(f"{prefix}.verified must be true")
    return errors
