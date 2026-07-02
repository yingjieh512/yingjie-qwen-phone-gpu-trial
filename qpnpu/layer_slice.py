"""Deterministic Phase 10 Qwen-like layer-slice artifact and checks."""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from qpnpu.model_format import load_tensor, read_model_metadata, validate_model_metadata, write_model_metadata
from qpnpu.toy_runtime import ByteTokenizerStub


DEFAULT_LAYER_SLICE_CONFIG: dict[str, Any] = {
    "architecture": "qwen_toy_layer_slice",
    "hf_id": "local/qwen-toy-layer-slice-smoke",
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
    "seed": 2026,
    "prompt": "hello",
    "seq_len": 8,
    "rms_norm_eps": 1.0e-6,
}

LAYER_SLICE_WARNINGS = [
    "Phase 10 layer-slice smoke only",
    "tiny deterministic Qwen-like slice; not Qwen 9B",
    "CPU Python reference only; not Android execution",
    "not NPU, QNN, NNAPI, or Vulkan execution",
    "not a performance claim",
]

REFERENCE_OUTPUT_NAMES = [
    "embedding",
    "input_rmsnorm",
    "q_rope",
    "k_rope",
    "attention_scores",
    "attention_probs",
    "attention_context",
    "attention_out",
    "post_attention_residual",
    "post_attention_rmsnorm",
    "mlp_gate",
    "mlp_up",
    "mlp_activation",
    "mlp_out",
    "final_hidden",
    "logits_last",
]


def create_layer_slice_model(
    model_dir: str | Path,
    config: dict[str, Any] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create a tiny deterministic one-layer Qwen-like slice artifact."""

    out = Path(model_dir)
    if out.exists() and any(out.iterdir()):
        if not overwrite:
            raise FileExistsError(f"refusing to overwrite existing layer-slice directory: {out}")
        _remove_existing_dir(out)
    out.mkdir(parents=True, exist_ok=True)

    merged = dict(DEFAULT_LAYER_SLICE_CONFIG)
    if config:
        merged.update(config)
    _validate_config(merged)

    tensors = _create_tensors(merged)
    tensor_entries = _write_tensor_bin(out / "model.bin", tensors)

    metadata = {
        "schema_version": "0.1",
        "format": "qpnpu",
        "model": {key: merged[key] for key in DEFAULT_LAYER_SLICE_CONFIG if key not in {"seed", "prompt", "seq_len", "rms_norm_eps"}},
        "tensors": tensor_entries,
        "phase": "10",
        "phase10_reference": {
            "file": "reference_outputs.json",
            "prompt": merged["prompt"],
            "seq_len": merged["seq_len"],
            "rms_norm_eps": merged["rms_norm_eps"],
            "outputs": REFERENCE_OUTPUT_NAMES,
        },
        "warnings": LAYER_SLICE_WARNINGS,
        "notes": [
            "This artifact validates per-operator and one-layer slice correctness plumbing.",
            "It is intentionally tiny and should not be interpreted as real Qwen 9B inference.",
        ],
    }
    write_model_metadata(out, metadata)

    reference = _build_reference_payload(metadata, tensors, str(merged["prompt"]), int(merged["seq_len"]))
    (out / "reference_outputs.json").write_text(
        json.dumps(reference, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_tokenizer_stub(out)
    _write_readme(out, metadata)
    return metadata


def run_layer_slice_check(
    model_dir: str | Path,
    *,
    prompt: str | None = None,
    tolerance: float = 1.0e-5,
) -> dict[str, Any]:
    """Run the Phase 10 reference ladder and compare with stored outputs."""

    root = Path(model_dir)
    metadata = read_model_metadata(root)
    errors = validate_model_metadata(metadata)
    if errors:
        raise ValueError("invalid layer-slice metadata: " + "; ".join(errors))
    model = metadata["model"]
    if model.get("architecture") != "qwen_toy_layer_slice":
        raise ValueError("Phase 10 layer-slice check requires architecture=qwen_toy_layer_slice")

    reference_info = metadata.get("phase10_reference", {})
    if not isinstance(reference_info, dict):
        raise ValueError("metadata.phase10_reference must be an object")
    reference_file = reference_info.get("file", "reference_outputs.json")
    if not isinstance(reference_file, str) or not reference_file:
        raise ValueError("metadata.phase10_reference.file must be a non-empty string")
    reference = json.loads((root / reference_file).read_text(encoding="utf-8"))
    if not isinstance(reference, dict):
        raise ValueError("reference outputs must be a JSON object")

    selected_prompt = prompt if prompt is not None else str(reference.get("prompt", reference_info.get("prompt", "hello")))
    seq_len = int(reference.get("seq_len", reference_info.get("seq_len", DEFAULT_LAYER_SLICE_CONFIG["seq_len"])))

    tensors = _load_tensors(root, metadata)
    start = time.perf_counter()
    token_ids, outputs, next_token_id = run_layer_slice_reference(metadata, tensors, selected_prompt, seq_len)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    expected_outputs = reference.get("outputs")
    if not isinstance(expected_outputs, dict):
        raise ValueError("reference_outputs.outputs must be an object")

    checks: list[dict[str, Any]] = []
    for name in REFERENCE_OUTPUT_NAMES:
        if name not in expected_outputs:
            checks.append(
                {
                    "name": name,
                    "passed": False,
                    "error": "missing expected output",
                    "max_abs_error": None,
                }
            )
            continue
        expected_entry = expected_outputs[name]
        if not isinstance(expected_entry, dict):
            checks.append({"name": name, "passed": False, "error": "expected output entry must be an object"})
            continue
        actual = outputs[name]
        expected = np.asarray(expected_entry.get("values"), dtype=np.float32)
        if tuple(expected.shape) != tuple(actual.shape):
            checks.append(
                {
                    "name": name,
                    "passed": False,
                    "error": f"shape mismatch: expected {list(expected.shape)}, actual {list(actual.shape)}",
                    "max_abs_error": None,
                }
            )
            continue
        max_abs_error = float(np.max(np.abs(actual - expected))) if actual.size else 0.0
        expected_sha = str(expected_entry.get("sha256", ""))
        actual_sha = _sha256_array(actual)
        checks.append(
            {
                "name": name,
                "shape": list(actual.shape),
                "dtype": "fp32",
                "max_abs_error": max_abs_error,
                "sha256_expected": expected_sha,
                "sha256_actual": actual_sha,
                "passed": max_abs_error <= tolerance,
            }
        )

    expected_next_token = reference.get("next_token_id")
    next_token_passed = expected_next_token == next_token_id
    all_passed = all(bool(item.get("passed")) for item in checks) and next_token_passed

    return {
        "schema_version": "0.1",
        "timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": "phase10-layer-slice-check",
        "backend": "cpu_python_reference",
        "model": {
            "architecture": model["architecture"],
            "hf_id": model["hf_id"],
            "hidden_size": model["hidden_size"],
            "num_layers": model["num_layers"],
            "num_attention_heads": model["num_attention_heads"],
            "intermediate_size": model["intermediate_size"],
            "vocab_size": model["vocab_size"],
        },
        "prompt": selected_prompt,
        "token_ids": token_ids,
        "checks": checks,
        "summary": {
            "all_passed": all_passed,
            "check_count": len(checks),
            "passed_check_count": sum(1 for item in checks if item.get("passed")),
            "next_token_id_expected": expected_next_token,
            "next_token_id_actual": next_token_id,
            "next_token_id_passed": next_token_passed,
            "latency_ms_total": elapsed_ms,
        },
        "warnings": LAYER_SLICE_WARNINGS,
    }


def validate_layer_slice_check_result(data: dict[str, Any]) -> list[str]:
    """Validate a Phase 10 layer-slice check JSON object."""

    if not isinstance(data, dict):
        return ["layer-slice check result must be a JSON object"]
    errors: list[str] = []
    for key in ["schema_version", "timestamp_utc", "source", "backend", "model", "prompt", "token_ids", "checks", "summary", "warnings"]:
        if key not in data:
            errors.append(f"missing required key: {key}")
    if data.get("schema_version") != "0.1":
        errors.append("schema_version must be 0.1")
    if data.get("source") != "phase10-layer-slice-check":
        errors.append("source must be phase10-layer-slice-check")
    if data.get("backend") != "cpu_python_reference":
        errors.append("backend must be cpu_python_reference")

    model = data.get("model")
    if not isinstance(model, dict):
        errors.append("model must be an object")
    elif model.get("architecture") != "qwen_toy_layer_slice":
        errors.append("model.architecture must be qwen_toy_layer_slice")

    if not isinstance(data.get("token_ids"), list) or not all(isinstance(item, int) for item in data.get("token_ids", [])):
        errors.append("token_ids must be a list of integers")

    checks = data.get("checks")
    if not isinstance(checks, list) or not checks:
        errors.append("checks must be a non-empty list")
    else:
        for index, check in enumerate(checks):
            if not isinstance(check, dict):
                errors.append(f"checks[{index}] must be an object")
                continue
            for key in ["name", "passed"]:
                if key not in check:
                    errors.append(f"checks[{index}] missing {key}")

    summary = data.get("summary")
    if not isinstance(summary, dict):
        errors.append("summary must be an object")
    elif summary.get("all_passed") is not True:
        errors.append("summary.all_passed must be true")

    warnings = data.get("warnings")
    if not isinstance(warnings, list):
        errors.append("warnings must be a list")
    else:
        joined = " ".join(str(item).lower() for item in warnings)
        for required in ["not qwen 9b", "not npu", "not a performance"]:
            if required not in joined:
                errors.append(f"warnings must mention {required}")
    return errors


def run_layer_slice_reference(
    metadata: dict[str, Any],
    tensors: dict[str, np.ndarray],
    prompt: str,
    seq_len: int,
) -> tuple[list[int], dict[str, np.ndarray], int]:
    """Run a tiny one-layer Qwen-like CPU reference and return intermediates."""

    model = metadata["model"]
    hidden_size = int(model["hidden_size"])
    num_heads = int(model["num_attention_heads"])
    head_dim = hidden_size // num_heads
    rope_theta = float(model["rope_theta"])
    eps = float(metadata.get("phase10_reference", {}).get("rms_norm_eps", DEFAULT_LAYER_SLICE_CONFIG["rms_norm_eps"]))

    token_ids = _fixed_length_token_ids(prompt, seq_len, int(model["vocab_size"]))
    embedding = tensors["token_embedding.weight"][token_ids]
    input_rmsnorm = _rms_norm_rows(embedding, tensors["layer.0.input_norm.weight"], eps)

    q = _linear(input_rmsnorm, tensors["layer.0.q_proj.weight"])
    k = _linear(input_rmsnorm, tensors["layer.0.k_proj.weight"])
    v = _linear(input_rmsnorm, tensors["layer.0.v_proj.weight"])
    q_rope = _apply_rope(q, num_heads, head_dim, rope_theta)
    k_rope = _apply_rope(k, num_heads, head_dim, rope_theta)

    attention_scores, attention_probs, attention_context = _attention(q_rope, k_rope, v, num_heads, head_dim)
    attention_out = _linear(attention_context, tensors["layer.0.o_proj.weight"])
    post_attention_residual = embedding + attention_out
    post_attention_rmsnorm = _rms_norm_rows(
        post_attention_residual,
        tensors["layer.0.post_attention_norm.weight"],
        eps,
    )

    mlp_gate = _linear(post_attention_rmsnorm, tensors["layer.0.mlp_gate.weight"])
    mlp_up = _linear(post_attention_rmsnorm, tensors["layer.0.mlp_up.weight"])
    mlp_activation = _silu(mlp_gate) * mlp_up
    mlp_out = _linear(mlp_activation, tensors["layer.0.mlp_down.weight"])
    final_hidden = post_attention_residual + mlp_out
    logits_last = tensors["lm_head.weight"] @ final_hidden[-1]
    next_token_id = int(np.argmax(logits_last))

    outputs = {
        "embedding": embedding.astype(np.float32),
        "input_rmsnorm": input_rmsnorm.astype(np.float32),
        "q_rope": q_rope.astype(np.float32),
        "k_rope": k_rope.astype(np.float32),
        "attention_scores": attention_scores.astype(np.float32),
        "attention_probs": attention_probs.astype(np.float32),
        "attention_context": attention_context.astype(np.float32),
        "attention_out": attention_out.astype(np.float32),
        "post_attention_residual": post_attention_residual.astype(np.float32),
        "post_attention_rmsnorm": post_attention_rmsnorm.astype(np.float32),
        "mlp_gate": mlp_gate.astype(np.float32),
        "mlp_up": mlp_up.astype(np.float32),
        "mlp_activation": mlp_activation.astype(np.float32),
        "mlp_out": mlp_out.astype(np.float32),
        "final_hidden": final_hidden.astype(np.float32),
        "logits_last": logits_last.astype(np.float32),
    }
    return token_ids, outputs, next_token_id


def _create_tensors(config: dict[str, Any]) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(int(config["seed"]))
    vocab_size = int(config["vocab_size"])
    hidden_size = int(config["hidden_size"])
    intermediate_size = int(config["intermediate_size"])

    def normal(shape: tuple[int, ...], scale: float = 0.02) -> np.ndarray:
        return rng.normal(0.0, scale, size=shape).astype(np.float32)

    return {
        "token_embedding.weight": normal((vocab_size, hidden_size)),
        "layer.0.input_norm.weight": np.linspace(0.97, 1.03, hidden_size, dtype=np.float32),
        "layer.0.q_proj.weight": normal((hidden_size, hidden_size)),
        "layer.0.k_proj.weight": normal((hidden_size, hidden_size)),
        "layer.0.v_proj.weight": normal((hidden_size, hidden_size)),
        "layer.0.o_proj.weight": normal((hidden_size, hidden_size)),
        "layer.0.post_attention_norm.weight": np.linspace(1.02, 0.98, hidden_size, dtype=np.float32),
        "layer.0.mlp_gate.weight": normal((intermediate_size, hidden_size)),
        "layer.0.mlp_up.weight": normal((intermediate_size, hidden_size)),
        "layer.0.mlp_down.weight": normal((hidden_size, intermediate_size)),
        "lm_head.weight": normal((vocab_size, hidden_size)),
    }


def _write_tensor_bin(path: Path, tensors: dict[str, np.ndarray]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    offset = 0
    with path.open("wb") as handle:
        for name, tensor in tensors.items():
            tensor_le = np.ascontiguousarray(tensor, dtype=np.dtype("<f4"))
            raw = tensor_le.tobytes(order="C")
            handle.write(raw)
            entries.append(
                {
                    "name": name,
                    "shape": list(tensor_le.shape),
                    "dtype": "fp32",
                    "quantization": "none",
                    "file": "model.bin",
                    "byte_offset": offset,
                    "byte_length": len(raw),
                }
            )
            offset += len(raw)
    return entries


def _build_reference_payload(
    metadata: dict[str, Any],
    tensors: dict[str, np.ndarray],
    prompt: str,
    seq_len: int,
) -> dict[str, Any]:
    token_ids, outputs, next_token_id = run_layer_slice_reference(metadata, tensors, prompt, seq_len)
    return {
        "schema_version": "0.1",
        "source": "phase10-layer-slice-reference",
        "prompt": prompt,
        "seq_len": seq_len,
        "token_ids": token_ids,
        "next_token_id": next_token_id,
        "outputs": {name: _serialize_array(outputs[name]) for name in REFERENCE_OUTPUT_NAMES},
        "warnings": LAYER_SLICE_WARNINGS,
    }


def _load_tensors(model_dir: Path, metadata: dict[str, Any]) -> dict[str, np.ndarray]:
    return {name: load_tensor(model_dir, metadata, name) for name in _required_tensor_names()}


def _required_tensor_names() -> list[str]:
    return [
        "token_embedding.weight",
        "layer.0.input_norm.weight",
        "layer.0.q_proj.weight",
        "layer.0.k_proj.weight",
        "layer.0.v_proj.weight",
        "layer.0.o_proj.weight",
        "layer.0.post_attention_norm.weight",
        "layer.0.mlp_gate.weight",
        "layer.0.mlp_up.weight",
        "layer.0.mlp_down.weight",
        "lm_head.weight",
    ]


def _serialize_array(array: np.ndarray) -> dict[str, Any]:
    contiguous = np.ascontiguousarray(array, dtype=np.dtype("<f4"))
    return {
        "shape": list(contiguous.shape),
        "dtype": "fp32",
        "sha256": _sha256_array(contiguous),
        "values": contiguous.tolist(),
    }


def _sha256_array(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array, dtype=np.dtype("<f4"))
    return hashlib.sha256(contiguous.tobytes(order="C")).hexdigest()


def _fixed_length_token_ids(prompt: str, seq_len: int, vocab_size: int) -> list[int]:
    token_ids = [token % vocab_size for token in ByteTokenizerStub().encode(prompt)]
    if not token_ids:
        token_ids = [0]
    if len(token_ids) < seq_len:
        token_ids = token_ids + [0] * (seq_len - len(token_ids))
    return token_ids[:seq_len]


def _linear(x: np.ndarray, weight: np.ndarray) -> np.ndarray:
    return (x @ weight.T).astype(np.float32)


def _rms_norm_rows(x: np.ndarray, weight: np.ndarray, eps: float) -> np.ndarray:
    variance = np.mean(np.square(x, dtype=np.float32), axis=-1, keepdims=True, dtype=np.float32)
    return (x / np.sqrt(variance + np.float32(eps))) * weight


def _apply_rope(x: np.ndarray, num_heads: int, head_dim: int, theta: float) -> np.ndarray:
    seq_len = x.shape[0]
    reshaped = x.reshape(seq_len, num_heads, head_dim).astype(np.float32).copy()
    half = head_dim // 2
    inv_freq = 1.0 / (float(theta) ** (np.arange(0, head_dim, 2, dtype=np.float32) / np.float32(head_dim)))
    positions = np.arange(seq_len, dtype=np.float32)
    angles = positions[:, None] * inv_freq[None, :]
    cos = np.cos(angles).astype(np.float32)
    sin = np.sin(angles).astype(np.float32)
    even = reshaped[:, :, 0::2].copy()
    odd = reshaped[:, :, 1::2].copy()
    reshaped[:, :, 0::2] = even * cos[:, None, :half] - odd * sin[:, None, :half]
    reshaped[:, :, 1::2] = even * sin[:, None, :half] + odd * cos[:, None, :half]
    return reshaped.reshape(seq_len, num_heads * head_dim)


def _attention(
    q: np.ndarray,
    k: np.ndarray,
    v: np.ndarray,
    num_heads: int,
    head_dim: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    seq_len = q.shape[0]
    qh = q.reshape(seq_len, num_heads, head_dim).transpose(1, 0, 2)
    kh = k.reshape(seq_len, num_heads, head_dim).transpose(1, 0, 2)
    vh = v.reshape(seq_len, num_heads, head_dim).transpose(1, 0, 2)
    scores = np.matmul(qh, np.swapaxes(kh, 1, 2)) / np.sqrt(np.float32(head_dim))
    causal_mask = np.triu(np.ones((seq_len, seq_len), dtype=bool), k=1)
    scores[:, causal_mask] = np.float32(-1.0e9)
    probs = _softmax(scores, axis=-1)
    context = np.matmul(probs, vh).transpose(1, 0, 2).reshape(seq_len, num_heads * head_dim)
    return scores.astype(np.float32), probs.astype(np.float32), context.astype(np.float32)


def _softmax(x: np.ndarray, axis: int) -> np.ndarray:
    shifted = x - np.max(x, axis=axis, keepdims=True)
    exp = np.exp(shifted).astype(np.float32)
    return exp / np.sum(exp, axis=axis, keepdims=True)


def _silu(x: np.ndarray) -> np.ndarray:
    return x / (1.0 + np.exp(-x))


def _validate_config(config: dict[str, Any]) -> None:
    if config.get("architecture") != "qwen_toy_layer_slice":
        raise ValueError("Phase 10 layer-slice architecture must be qwen_toy_layer_slice")
    if config.get("dtype") != "fp32":
        raise ValueError("Phase 10 layer-slice only supports fp32")
    if config.get("quantization") != "none":
        raise ValueError("Phase 10 layer-slice only supports quantization=none")
    for key in [
        "hidden_size",
        "num_layers",
        "num_attention_heads",
        "num_key_value_heads",
        "intermediate_size",
        "vocab_size",
        "max_position_embeddings",
        "seed",
        "seq_len",
    ]:
        value = config.get(key)
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"{key} must be a positive integer")
    hidden_size = int(config["hidden_size"])
    num_heads = int(config["num_attention_heads"])
    if hidden_size % num_heads != 0:
        raise ValueError("hidden_size must be divisible by num_attention_heads")
    if (hidden_size // num_heads) % 2 != 0:
        raise ValueError("head_dim must be even for RoPE")
    if config["num_key_value_heads"] != num_heads:
        raise ValueError("Phase 10 layer-slice currently requires num_key_value_heads == num_attention_heads")
    if int(config["vocab_size"]) > 256:
        raise ValueError("ByteTokenizerStub supports vocab_size up to 256")
    if int(config["seq_len"]) > int(config["max_position_embeddings"]):
        raise ValueError("seq_len must be <= max_position_embeddings")
    if not isinstance(config.get("rope_theta"), (int, float)) or float(config["rope_theta"]) <= 0.0:
        raise ValueError("rope_theta must be positive")
    if not isinstance(config.get("rms_norm_eps"), (int, float)) or float(config["rms_norm_eps"]) <= 0.0:
        raise ValueError("rms_norm_eps must be positive")


def _remove_existing_dir(path: Path) -> None:
    resolved = path.resolve()
    cwd = Path.cwd().resolve()
    if resolved == cwd or resolved.parent == resolved:
        raise ValueError(f"refusing to overwrite unsafe directory: {path}")
    shutil.rmtree(path)


def _write_tokenizer_stub(model_dir: Path) -> None:
    payload = {
        "schema_version": "0.1",
        "type": "byte_tokenizer_stub",
        "vocab_size": 256,
        "description": "Encodes UTF-8 bytes directly as token ids 0..255 for Phase 10 slice checks.",
        "warnings": [
            "This is not the Qwen tokenizer.",
            "It exists only for deterministic layer-slice smoke tests.",
        ],
    }
    (model_dir / "tokenizer_stub.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_readme(model_dir: Path, metadata: dict[str, Any]) -> None:
    model = metadata["model"]
    text = f"""# Phase 10 Toy Layer Slice

This directory contains a tiny deterministic QPNPU one-layer slice artifact.

It validates reference math and tensor format plumbing for embedding, RMSNorm, linear projections, RoPE, causal softmax attention, MLP, and final logits. It is not Qwen 9B, not a complete transformer runtime, not Android execution, not NPU or QNN execution, and not a performance claim.

## Contents

- `metadata.json`: QPNPU tensor metadata.
- `model.bin`: fp32 tensor bytes for the tiny slice.
- `reference_outputs.json`: deterministic expected intermediate outputs.
- `tokenizer_stub.json`: byte-level tokenizer stub metadata.

## Model Summary

- architecture: {model['architecture']}
- hf_id: {model['hf_id']}
- hidden_size: {model['hidden_size']}
- num_layers: {model['num_layers']}
- num_attention_heads: {model['num_attention_heads']}
- intermediate_size: {model['intermediate_size']}
- vocab_size: {model['vocab_size']}
"""
    (model_dir / "README.md").write_text(text, encoding="utf-8")
