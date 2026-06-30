#!/usr/bin/env python
"""Select best benchmark results for each operator and shape group."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qpnpu.benchmark import select_best_benchmarks, validate_benchmark_result  # noqa: E402
from qpnpu.config import load_json  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmarks", nargs="+", help="One or more benchmark JSON files.")
    parser.add_argument("--out", help="Optional output JSON with selected result summaries.")
    args = parser.parse_args(argv)

    results = []
    for path in args.benchmarks:
        result = load_json(path)
        errors = validate_benchmark_result(result)
        if errors:
            print(f"benchmark validation failed for {path}:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 2
        results.append(result)

    selected = select_best_benchmarks(results)
    print("selected benchmark results:")
    for group, result in selected.items():
        metrics = result.get("metrics", {})
        print(
            f"  - {group}: backend={result.get('backend')} "
            f"tokens_per_second={metrics.get('tokens_per_second')} "
            f"latency_ms_p50={metrics.get('latency_ms_p50')} "
            f"kernel_config_hash={result.get('kernel_config_hash')}"
        )

    if args.out:
        payload = {
            "schema_version": "0.1",
            "selected": [
                {
                    "group": group,
                    "kernel_config_hash": result.get("kernel_config_hash"),
                    "kernel_config": result.get("kernel_config"),
                    "source_result": result,
                }
                for group, result in selected.items()
            ],
        }
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote selected config summary: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

