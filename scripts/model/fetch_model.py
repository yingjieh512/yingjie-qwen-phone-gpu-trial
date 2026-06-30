#!/usr/bin/env python
"""Plan a future Hugging Face model download without downloading files."""

from __future__ import annotations

import argparse
import shlex


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hf-id", default="Qwen/Qwen-placeholder-9B", help="Hugging Face model id.")
    parser.add_argument("--local-dir", default="./models/qwen", help="Local destination directory.")
    args = parser.parse_args(argv)

    command = f"huggingface-cli download {shlex.quote(args.hf_id)} --local-dir {shlex.quote(args.local_dir)}"
    print("Phase 0 dry run: no model files will be downloaded.")
    print(f"Intended command: {command}")
    print("Review model license, storage needs, and credentials before running a real download in a later phase.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

