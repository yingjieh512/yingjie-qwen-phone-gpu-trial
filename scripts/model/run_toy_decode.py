#!/usr/bin/env python
"""Run deterministic CPU-only toy decode and write benchmark JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qpnpu.benchmark import validate_benchmark_result  # noqa: E402
from qpnpu.config import utc_now_iso  # noqa: E402
from qpnpu.toy_model import TOY_MODEL_WARNINGS  # noqa: E402
from qpnpu.toy_runtime import ToyQwenRuntime  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", required=True, help="QPNPU toy model directory.")
    parser.add_argument("--prompt", required=True, help="Prompt text to byte-tokenize.")
    parser.add_argument("--max-new-tokens", type=int, required=True, help="Number of toy tokens to generate.")
    parser.add_argument("--out", required=True, help="Output JSON path.")
    args = parser.parse_args(argv)

    try:
        runtime = ToyQwenRuntime(Path(args.model_dir))
        generation = runtime.generate(args.prompt, args.max_new_tokens)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    timestamp = utc_now_iso()
    model = runtime.model
    latency_ms = float(generation["latency_ms_total"])
    benchmark = {
        "schema_version": "0.1",
        "timestamp_utc": timestamp,
        "device": {"type": "local_host"},
        "model": {
            "architecture": model["architecture"],
            "hf_id": model["hf_id"],
        },
        "backend": ToyQwenRuntime.backend,
        "operator": "toy_decode",
        "shape": {
            "max_new_tokens": args.max_new_tokens,
            "hidden_size": model["hidden_size"],
            "vocab_size": model["vocab_size"],
        },
        "metrics": {
            "latency_ms_p50": latency_ms,
            "latency_ms_p90": latency_ms,
            "latency_ms_p99": latency_ms,
            "tokens_per_second": float(generation["tokens_per_second"]),
            "memory_rss_mb": 0.0,
        },
        "thermal": {},
        "kernel_config_hash": "toy",
        "warnings": ["toy local CPU benchmark; not a phone, NPU, or Qwen 9B performance claim"],
    }
    errors = validate_benchmark_result(benchmark)
    if errors:
        print("error: generated benchmark object failed validation:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    output: dict[str, Any] = {
        "schema_version": "0.1",
        "timestamp_utc": timestamp,
        "source": "toy-runtime",
        "model": {
            "architecture": model["architecture"],
            "hf_id": model["hf_id"],
            "hidden_size": model["hidden_size"],
            "num_layers": model["num_layers"],
            "vocab_size": model["vocab_size"],
        },
        "backend": ToyQwenRuntime.backend,
        "prompt": generation["prompt"],
        "prompt_token_ids": generation["prompt_token_ids"],
        "generated_token_ids": generation["generated_token_ids"],
        "generated_text": generation["generated_text"],
        "benchmark": benchmark,
        "warnings": TOY_MODEL_WARNINGS,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote toy decode JSON: {out_path}")
    print(f"generated_token_ids: {generation['generated_token_ids']}")
    print(f"generated_text: {ascii(generation['generated_text'])}")
    for warning in TOY_MODEL_WARNINGS:
        print(f"warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())