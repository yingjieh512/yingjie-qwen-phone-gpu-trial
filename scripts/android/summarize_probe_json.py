#!/usr/bin/env python
"""Summarize Android QPNPU probe JSON into a target hardware profile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qpnpu.android_probe import (  # noqa: E402
    read_android_probe,
    render_android_probe_summary,
    summarize_android_probe,
    write_summary_json,
    write_summary_markdown,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Android probe JSON path.")
    parser.add_argument("--out-json", help="Optional compact summary JSON output path.")
    parser.add_argument("--out-md", help="Optional markdown target profile output path.")
    args = parser.parse_args(argv)

    try:
        probe = read_android_probe(args.input)
        summary = summarize_android_probe(probe)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(render_android_probe_summary(summary))
    if args.out_json:
        path = write_summary_json(args.out_json, summary)
        print(f"wrote summary JSON: {path}")
    if args.out_md:
        path = write_summary_markdown(args.out_md, summary)
        print(f"wrote markdown profile: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
