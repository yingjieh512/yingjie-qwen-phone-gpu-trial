#!/usr/bin/env python
"""Inspect Hugging Face config.json or QPNPU metadata.json model artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qpnpu.model_format import read_model_metadata, tensor_index, validate_model_metadata  # noqa: E402


KNOWN_FIELDS = [
    "model_type",
    "architectures",
    "hidden_size",
    "num_hidden_layers",
    "num_attention_heads",
    "num_key_value_heads",
    "vocab_size",
    "torch_dtype",
    "max_position_embeddings",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Path to a Hugging Face-style config.json file.")
    parser.add_argument("--model-dir", help="Path to a QPNPU model directory containing metadata.json.")
    args = parser.parse_args(argv)

    if not args.config and not args.model_dir:
        parser.error("one of --config or --model-dir is required")

    exit_code = 0
    if args.config:
        exit_code = max(exit_code, _inspect_hf_config(Path(args.config)))
    if args.model_dir:
        exit_code = max(exit_code, _inspect_qpnpu_model(Path(args.model_dir)))
    return exit_code


def _inspect_hf_config(config_path: Path) -> int:
    if not config_path.exists():
        print(f"error: config does not exist: {config_path}", file=sys.stderr)
        return 2

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {config_path}: {exc}", file=sys.stderr)
        return 2

    if not isinstance(data, dict):
        print(f"error: expected JSON object in {config_path}", file=sys.stderr)
        return 2

    print("Hugging Face config summary")
    print(f"path: {config_path}")
    for field in KNOWN_FIELDS:
        print(f"{field}: {data.get(field, '<missing>')}")
    return 0


def _inspect_qpnpu_model(model_dir: Path) -> int:
    metadata_path = model_dir / "metadata.json"
    if not metadata_path.exists():
        print(f"error: metadata.json does not exist under: {model_dir}", file=sys.stderr)
        return 2

    try:
        metadata = read_model_metadata(model_dir)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: failed to read QPNPU metadata: {exc}", file=sys.stderr)
        return 2

    errors = validate_model_metadata(metadata)
    if errors:
        print("error: invalid QPNPU metadata:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    model = metadata["model"]
    tensors = tensor_index(metadata)
    total_bytes = sum(int(tensor["byte_length"]) for tensor in tensors.values())
    total_params = 0
    for tensor in tensors.values():
        params = 1
        for dim in tensor["shape"]:
            params *= int(dim)
        total_params += params

    print("QPNPU model summary")
    print(f"path: {model_dir}")
    print(f"schema_version: {metadata['schema_version']}")
    print(f"format: {metadata['format']}")
    print(f"architecture: {model['architecture']}")
    print(f"hf_id: {model['hf_id']}")
    print(f"hidden_size: {model['hidden_size']}")
    print(f"num_layers: {model['num_layers']}")
    print(f"vocab_size: {model['vocab_size']}")
    print(f"dtype: {model['dtype']}")
    print(f"quantization: {model['quantization']}")
    print(f"tensor_count: {len(tensors)}")
    print(f"parameter_count_estimate: {total_params}")
    print(f"parameter_memory_bytes: {total_bytes}")
    print("tensors:")
    for name in sorted(tensors):
        tensor = tensors[name]
        print(
            "  - "
            f"{name}: shape={tensor['shape']}, dtype={tensor['dtype']}, "
            f"file={tensor['file']}, offset={tensor['byte_offset']}, bytes={tensor['byte_length']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())