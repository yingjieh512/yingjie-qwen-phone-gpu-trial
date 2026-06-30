#!/usr/bin/env python
"""Build a Phase 1 probe_result.json from raw host-side ADB probe files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qpnpu.adb_probe import write_probe_result  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", required=True, help="Directory containing raw_*.txt files from ADB collection.")
    parser.add_argument("--out", required=True, help="Output probe_result.json path.")
    args = parser.parse_args(argv)

    try:
        write_probe_result(Path(args.raw_dir), Path(args.out))
    except Exception as exc:  # noqa: BLE001 - CLI should report parser failures cleanly.
        print(f"error: failed to build probe JSON: {exc}", file=sys.stderr)
        return 2

    print(f"wrote probe JSON: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

