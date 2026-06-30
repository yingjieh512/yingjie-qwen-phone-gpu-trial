#!/usr/bin/env python
"""Dry-run the future Android autotuning workflow."""

from __future__ import annotations

import argparse


DRY_RUN_STEPS = [
    "read probe",
    "generate candidate kernels",
    "build native library",
    "deploy to Android",
    "run microbenchmarks",
    "pull results",
    "select kernel config",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print planned steps without requiring hardware.")
    parser.add_argument("--probe-file", default="./benchmarks/results/latest_probe.json", help="Future probe JSON path.")
    parser.add_argument("--model-metadata", default="./models/qwen/model.qpnpu.json", help="Future model metadata path.")
    args = parser.parse_args(argv)

    if not args.dry_run:
        print("Phase 0 only supports planning. Re-run with --dry-run to print the workflow.")
        return 0

    print("Phase 0 autotune dry run")
    print(f"probe file: {args.probe_file}")
    print(f"model metadata: {args.model_metadata}")
    for index, step in enumerate(DRY_RUN_STEPS, start=1):
        print(f"{index}. {step}")
    print("No Android hardware, build system, or benchmark execution is required in Phase 0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

