#!/usr/bin/env python
"""Create a tiny deterministic QPNPU toy Qwen-like smoke model."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qpnpu.model_format import validate_model_metadata  # noqa: E402
from qpnpu.toy_model import TOY_MODEL_WARNINGS, create_toy_model  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="Output model directory.")
    parser.add_argument("--hidden-size", type=int, default=32, help="Toy hidden size.")
    parser.add_argument("--vocab-size", type=int, default=256, help="Toy byte vocabulary size, max 256.")
    parser.add_argument("--seed", type=int, default=1234, help="Deterministic tensor seed.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output directory.")
    args = parser.parse_args(argv)

    config = {
        "hidden_size": args.hidden_size,
        "vocab_size": args.vocab_size,
        "seed": args.seed,
    }
    try:
        metadata = create_toy_model(Path(args.out), config=config, overwrite=args.overwrite)
    except (FileExistsError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    errors = validate_model_metadata(metadata)
    if errors:
        print("error: created metadata failed validation:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    output_dir = Path(args.out)
    model_bin = output_dir / "model.bin"
    model = metadata["model"]
    print(f"wrote toy model: {output_dir}")
    print(f"tensor file: {model_bin} ({model_bin.stat().st_size} bytes)")
    print(
        "metadata: "
        f"architecture={model['architecture']}, "
        f"hidden_size={model['hidden_size']}, "
        f"vocab_size={model['vocab_size']}, "
        f"tensors={len(metadata['tensors'])}"
    )
    for warning in TOY_MODEL_WARNINGS:
        print(f"warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())