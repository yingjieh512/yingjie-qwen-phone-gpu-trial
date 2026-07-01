#!/usr/bin/env python
"""Extract QPNPU probe JSON from AWS Device Farm logcat text."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qpnpu.android_logcat import write_extracted_probe_json  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logcat", required=True, help="Downloaded or pasted logcat text file.")
    parser.add_argument("--out", required=True, help="Clean probe JSON output path.")
    args = parser.parse_args(argv)

    try:
        out = write_extracted_probe_json(args.logcat, args.out)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote extracted probe JSON: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
