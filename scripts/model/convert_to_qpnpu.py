#!/usr/bin/env python
"""Plan conversion from future model artifacts into QPNPU metadata."""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="./models/qwen", help="Input model directory for a later phase.")
    parser.add_argument("--output", default="./models/qwen.qpnpu", help="Output QPNPU artifact directory.")
    parser.add_argument("--dry-run", action="store_true", help="Print the planned conversion and exit.")
    args = parser.parse_args(argv)

    mode = "dry run" if args.dry_run else "Phase 0 planning mode"
    print(f"{mode}: no conversion is performed.")
    print(f"planned input: {args.input}")
    print(f"planned output: {args.output}")
    print("Future work: validate metadata, map tensor manifests, and emit QPNPU files.")
    print("Safetensors conversion is not implemented in Phase 0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

