#!/usr/bin/env python
"""Convert a tiny local .npy tensor fixture into QPNPU format."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qpnpu.model_format import validate_model_metadata, write_model_metadata  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="./models/qwen", help="Unsupported future input model directory.")
    parser.add_argument("--output", default="./models/qwen.qpnpu", help="Legacy output directory alias.")
    parser.add_argument("--input-npy", help="Path to a small local .npy tensor fixture.")
    parser.add_argument("--tensor-name", default="fixture.weight", help="Tensor name for --input-npy conversion.")
    parser.add_argument("--output-dir", help="Output QPNPU artifact directory.")
    parser.add_argument("--dry-run", action="store_true", help="Print the planned conversion and exit.")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir or args.output)
    if args.input_npy:
        return _convert_npy(Path(args.input_npy), args.tensor_name, output_dir, args.dry_run)

    if args.input != "./models/qwen" and not args.dry_run:
        print("error: only --input-npy conversion is implemented in Phase 3.", file=sys.stderr)
        print("safetensors or full model directory conversion remains future work.", file=sys.stderr)
        return 2

    mode = "dry run" if args.dry_run else "Phase 3 planning mode"
    print(f"{mode}: no full model conversion is performed.")
    print(f"planned input: {args.input}")
    print(f"planned output: {output_dir}")
    print("Supported now: --input-npy PATH --tensor-name NAME --output-dir PATH for small local fixtures.")
    print("Safetensors and full Qwen conversion are not implemented in Phase 3.")
    return 0


def _convert_npy(input_npy: Path, tensor_name: str, output_dir: Path, dry_run: bool) -> int:
    if not input_npy.exists():
        print(f"error: input .npy file does not exist: {input_npy}", file=sys.stderr)
        return 2
    if not tensor_name:
        print("error: --tensor-name must not be empty", file=sys.stderr)
        return 2

    try:
        array = np.load(input_npy)
    except ValueError as exc:
        print(f"error: failed to load .npy tensor: {exc}", file=sys.stderr)
        return 2
    if not np.issubdtype(array.dtype, np.number):
        print(f"error: .npy tensor must contain numeric data, got {array.dtype}", file=sys.stderr)
        return 2
    tensor = np.ascontiguousarray(array.astype(np.float32, copy=False), dtype=np.dtype("<f4"))

    if dry_run:
        print("dry run: would convert small .npy tensor to QPNPU format")
        print(f"input_npy: {input_npy}")
        print(f"tensor_name: {tensor_name}")
        print(f"shape: {list(tensor.shape)}")
        print(f"dtype: fp32")
        print(f"output_dir: {output_dir}")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    raw = tensor.tobytes(order="C")
    (output_dir / "model.bin").write_bytes(raw)
    metadata = _metadata_for_tensor(tensor_name, list(tensor.shape), len(raw))
    errors = validate_model_metadata(metadata)
    if errors:
        print("error: generated metadata failed validation:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2
    write_model_metadata(output_dir, metadata)
    print(f"wrote QPNPU fixture: {output_dir}")
    print(f"tensor: {tensor_name}, shape={list(tensor.shape)}, dtype=fp32, bytes={len(raw)}")
    print("warning: this is a one-tensor fixture conversion, not full safetensors or Qwen conversion")
    return 0


def _metadata_for_tensor(tensor_name: str, shape: list[int], byte_length: int) -> dict[str, Any]:
    hidden_size = int(shape[-1]) if shape else 1
    vocab_size = int(shape[0]) if shape else 1
    return {
        "schema_version": "0.1",
        "format": "qpnpu",
        "model": {
            "architecture": "npy_fixture",
            "hf_id": "local/npy-fixture",
            "hidden_size": hidden_size,
            "num_layers": 0,
            "num_attention_heads": 0,
            "num_key_value_heads": 0,
            "intermediate_size": 0,
            "vocab_size": vocab_size,
            "max_position_embeddings": 0,
            "rope_theta": 10000.0,
            "dtype": "fp32",
            "quantization": "none",
        },
        "tensors": [
            {
                "name": tensor_name,
                "shape": shape,
                "dtype": "fp32",
                "quantization": "none",
                "file": "model.bin",
                "byte_offset": 0,
                "byte_length": byte_length,
            }
        ],
        "warnings": ["one-tensor local fixture only; not full Qwen conversion"],
    }


if __name__ == "__main__":
    raise SystemExit(main())