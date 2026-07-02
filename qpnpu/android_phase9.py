"""Validation helpers for Android Phase 9 native cached-shard loader payloads."""

from __future__ import annotations

from typing import Any

from qpnpu.android_toy_decode import validate_android_toy_decode


REQUIRED_PHASE9_KEYS = [
    "schema_version",
    "source",
    "backend",
    "native_library",
    "model",
    "model_delivery",
    "native_model_loader",
    "toy_decode",
    "generated_token_ids",
    "warnings",
]


def validate_phase9_native_shard_loader(data: dict[str, Any]) -> list[str]:
    """Validate a Phase 9 Android native cached-shard loader payload."""

    if not isinstance(data, dict):
        return ["Phase 9 payload must be a JSON object"]

    errors: list[str] = []
    for key in REQUIRED_PHASE9_KEYS:
        if key not in data:
            errors.append(f"missing required key: {key}")

    if data.get("source") != "android-phase9-native-shard-loader":
        errors.append("source must be android-phase9-native-shard-loader")
    if data.get("backend") != "cpu_android_native_file_loader":
        errors.append("backend must be cpu_android_native_file_loader")

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
        if delivery.get("all_sha256_verified") is not True:
            errors.append("model_delivery.all_sha256_verified must be true")
        if not isinstance(delivery.get("files"), list) or not delivery.get("files"):
            errors.append("model_delivery.files must be a non-empty list")

    loader = data.get("native_model_loader")
    if not isinstance(loader, dict):
        errors.append("native_model_loader must be an object")
    else:
        if loader.get("loader_location") != "native_jni":
            errors.append("native_model_loader.loader_location must be native_jni")
        if loader.get("open_method") != "mmap_readonly":
            errors.append("native_model_loader.open_method must be mmap_readonly")
        if loader.get("java_tensor_bytes_passed") is not False:
            errors.append("native_model_loader.java_tensor_bytes_passed must be false")
        if loader.get("all_sha256_verified_before_native_load") is not True:
            errors.append("native_model_loader.all_sha256_verified_before_native_load must be true")
        if not isinstance(loader.get("metadata_path"), str) or not loader.get("metadata_path"):
            errors.append("native_model_loader.metadata_path must be a non-empty string")
        paths = loader.get("tensor_shard_paths")
        if not isinstance(paths, list) or not paths:
            errors.append("native_model_loader.tensor_shard_paths must be a non-empty list")
        elif loader.get("tensor_shard_count") != len(paths):
            errors.append("native_model_loader.tensor_shard_count must match tensor_shard_paths length")
        if not isinstance(loader.get("tensor_bytes"), int) or loader.get("tensor_bytes") <= 0:
            errors.append("native_model_loader.tensor_bytes must be a positive integer")

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
        for required in ["native", "shard", "toy", "not qwen 9b", "not npu", "not a performance"]:
            if required not in joined:
                errors.append(f"warnings must mention {required}")
    elif "warnings" in data:
        errors.append("warnings must be a list")

    return errors
