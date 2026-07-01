"""Validation helpers for Android Phase 7B toy decode payloads."""

from __future__ import annotations

from typing import Any

from qpnpu.benchmark import validate_benchmark_result


REQUIRED_TOY_DECODE_KEYS = [
    "schema_version",
    "source",
    "backend",
    "native_library",
    "model",
    "asset_model",
    "tokenizer",
    "prompt",
    "prompt_token_ids",
    "generated_token_ids",
    "generated_text",
    "decode",
    "benchmark",
    "warnings",
]


def validate_android_toy_decode(data: dict[str, Any]) -> list[str]:
    """Validate an Android toy decode JSON object."""

    if not isinstance(data, dict):
        return ["android toy decode payload must be a JSON object"]

    errors: list[str] = []
    for key in REQUIRED_TOY_DECODE_KEYS:
        if key not in data:
            errors.append(f"missing required key: {key}")

    if data.get("source") != "android-toy-decode":
        errors.append("source must be android-toy-decode")
    if data.get("backend") != "cpu_android_native_reference":
        errors.append("backend must be cpu_android_native_reference")

    for key in ["model", "asset_model", "tokenizer", "decode", "benchmark"]:
        if key in data and not isinstance(data[key], dict):
            errors.append(f"{key} must be an object")

    if "prompt" in data and not isinstance(data["prompt"], str):
        errors.append("prompt must be a string")
    if "generated_text" in data and not isinstance(data["generated_text"], str):
        errors.append("generated_text must be a string")
    if "warnings" in data and not isinstance(data["warnings"], list):
        errors.append("warnings must be a list")

    for key in ["prompt_token_ids", "generated_token_ids"]:
        value = data.get(key)
        if not isinstance(value, list):
            errors.append(f"{key} must be a list")
        else:
            for index, token_id in enumerate(value):
                if not isinstance(token_id, int) or token_id < 0 or token_id > 255:
                    errors.append(f"{key}[{index}] must be an integer token id in range 0..255")

    model = data.get("model")
    if isinstance(model, dict):
        if model.get("architecture") != "qwen_toy":
            errors.append("model.architecture must be qwen_toy")
        for key in ["hidden_size", "num_layers", "vocab_size"]:
            if not isinstance(model.get(key), int) or model.get(key) <= 0:
                errors.append(f"model.{key} must be a positive integer")

    asset_model = data.get("asset_model")
    if isinstance(asset_model, dict):
        for key in ["metadata_asset", "tensor_asset"]:
            if not isinstance(asset_model.get(key), str) or not asset_model.get(key):
                errors.append(f"asset_model.{key} must be a non-empty string")
        if not isinstance(asset_model.get("tensor_bytes"), int) or asset_model.get("tensor_bytes") <= 0:
            errors.append("asset_model.tensor_bytes must be a positive integer")

    tokenizer = data.get("tokenizer")
    if isinstance(tokenizer, dict):
        if tokenizer.get("type") != "byte_tokenizer_stub":
            errors.append("tokenizer.type must be byte_tokenizer_stub")
        if tokenizer.get("is_qwen_tokenizer") is not False:
            errors.append("tokenizer.is_qwen_tokenizer must be false")

    decode = data.get("decode")
    generated = data.get("generated_token_ids") if isinstance(data.get("generated_token_ids"), list) else []
    if isinstance(decode, dict):
        max_new_tokens = decode.get("max_new_tokens")
        if not isinstance(max_new_tokens, int) or max_new_tokens < 0:
            errors.append("decode.max_new_tokens must be a non-negative integer")
        elif len(generated) != max_new_tokens:
            errors.append("generated_token_ids length must equal decode.max_new_tokens")
        for key in ["latency_ms_total", "tokens_per_second"]:
            if not isinstance(decode.get(key), (int, float)):
                errors.append(f"decode.{key} must be numeric")

    benchmark = data.get("benchmark")
    if isinstance(benchmark, dict):
        errors.extend(f"benchmark: {error}" for error in validate_benchmark_result(benchmark))
        if benchmark.get("operator") != "toy_decode":
            errors.append("benchmark.operator must be toy_decode")

    warnings = data.get("warnings")
    if isinstance(warnings, list):
        joined = " ".join(str(item).lower() for item in warnings)
        for required in ["toy", "not qwen 9b", "not npu", "not a performance"]:
            if required not in joined:
                errors.append(f"warnings must mention {required}")

    return errors