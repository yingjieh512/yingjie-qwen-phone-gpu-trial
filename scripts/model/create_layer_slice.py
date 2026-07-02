#!/usr/bin/env python
"""Create a tiny deterministic Phase 10 Qwen-like layer-slice artifact."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qpnpu.layer_slice import create_layer_slice_model  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="Output model directory.")
    parser.add_argument("--hidden-size", type=int, default=32)
    parser.add_argument("--intermediate-size", type=int, default=64)
    parser.add_argument("--num-heads", type=int, default=4)
    parser.add_argument("--seq-len", type=int, default=8)
    parser.add_argument("--prompt", default="hello")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    try:
        metadata = create_layer_slice_model(
            Path(args.out),
            {
                "hidden_size": args.hidden_size,
                "intermediate_size": args.intermediate_size,
                "num_attention_heads": args.num_heads,
                "num_key_value_heads": args.num_heads,
                "seq_len": args.seq_len,
                "prompt": args.prompt,
                "seed": args.seed,
            },
            overwrite=args.overwrite,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    out = Path(args.out)
    tensor_bytes = (out / "model.bin").stat().st_size
    print(f"wrote Phase 10 layer-slice artifact: {out}")
    print(f"tensor bytes: {tensor_bytes}")
    print(f"tensor count: {len(metadata['tensors'])}")
    print(f"reference file: {out / 'reference_outputs.json'}")
    print("warning: tiny layer-slice smoke only; not Qwen 9B, not NPU, not a performance claim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
