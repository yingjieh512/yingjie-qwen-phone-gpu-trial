#!/usr/bin/env python
"""Build an execution-model-neutral hardware characterization from Android probe JSON."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qpnpu.hardware_characterization import (  # noqa: E402
    read_and_characterize_android_probe,
    render_hardware_model_markdown,
    write_hardware_model_json,
    write_hardware_model_markdown,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Android probe JSON path.")
    parser.add_argument("--out-json", help="Optional hardware model JSON output path.")
    parser.add_argument("--out-md", help="Optional markdown hardware model output path.")
    args = parser.parse_args(argv)

    try:
        model = read_and_characterize_android_probe(args.input)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(render_hardware_model_markdown(model))
    if args.out_json:
        path = write_hardware_model_json(args.out_json, model)
        print(f"wrote hardware model JSON: {path}")
    if args.out_md:
        path = write_hardware_model_markdown(args.out_md, model)
        print(f"wrote hardware model markdown: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
