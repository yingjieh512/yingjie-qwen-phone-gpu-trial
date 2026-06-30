#!/usr/bin/env python
"""Inspect a Hugging Face-style config.json file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


KNOWN_FIELDS = [
    "model_type",
    "architectures",
    "hidden_size",
    "num_hidden_layers",
    "num_attention_heads",
    "num_key_value_heads",
    "vocab_size",
    "torch_dtype",
    "max_position_embeddings",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to a Hugging Face-style config.json file.")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"error: config does not exist: {config_path}", file=sys.stderr)
        return 2

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {config_path}: {exc}", file=sys.stderr)
        return 2

    if not isinstance(data, dict):
        print(f"error: expected JSON object in {config_path}", file=sys.stderr)
        return 2

    print("Hugging Face config summary")
    print(f"path: {config_path}")
    for field in KNOWN_FIELDS:
        print(f"{field}: {data.get(field, '<missing>')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

