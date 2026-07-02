#!/usr/bin/env python
"""Run the Phase 10 layer-slice correctness ladder."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qpnpu.layer_slice import run_layer_slice_check, validate_layer_slice_check_result  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--prompt", default=None, help="Optional prompt override. Defaults to the stored reference prompt.")
    parser.add_argument("--out", required=True, help="Output JSON path.")
    parser.add_argument("--tolerance", type=float, default=1.0e-5)
    args = parser.parse_args(argv)

    try:
        result = run_layer_slice_check(Path(args.model_dir), prompt=args.prompt, tolerance=args.tolerance)
        errors = validate_layer_slice_check_result(result)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if errors:
        print("error: generated layer-slice check result did not validate:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = result["summary"]
    print(f"wrote layer-slice check JSON: {out}")
    print(f"checks passed: {summary['passed_check_count']}/{summary['check_count']}")
    print(f"next token id: {summary['next_token_id_actual']}")
    print("warning: correctness ladder only; not Qwen 9B, not NPU, not a performance claim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
