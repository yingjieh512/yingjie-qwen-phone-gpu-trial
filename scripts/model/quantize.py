#!/usr/bin/env python
"""Quantize a small NumPy matrix fixture with Phase 0 int4 helpers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qpnpu.quant import symmetric_int4_quantize  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-npy", help="Optional path to a small 2D .npy matrix fixture.")
    parser.add_argument("--output-dir", default="./models/quantized", help="Directory for packed.npy and scales.npy.")
    parser.add_argument("--group-size", type=int, default=128, help="Group size along the last dimension.")
    args = parser.parse_args(argv)

    if not args.input_npy:
        print("Phase 0 dry run: provide --input-npy to quantize a small local fixture.")
        print(f"planned output directory: {args.output_dir}")
        print(f"group size: {args.group_size}")
        return 0

    input_path = Path(args.input_npy)
    if not input_path.exists():
        print(f"error: input .npy file does not exist: {input_path}", file=sys.stderr)
        return 2

    matrix = np.load(input_path)
    packed, scales = symmetric_int4_quantize(matrix, group_size=args.group_size)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    np.save(output_dir / "packed.npy", packed)
    np.save(output_dir / "scales.npy", scales)

    print(f"quantized fixture: {input_path}")
    print(f"packed shape: {packed.shape}, dtype: {packed.dtype}")
    print(f"scales shape: {scales.shape}, dtype: {scales.dtype}")
    print(f"wrote: {output_dir / 'packed.npy'}")
    print(f"wrote: {output_dir / 'scales.npy'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

