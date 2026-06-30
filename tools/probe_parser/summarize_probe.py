#!/usr/bin/env python
"""Summarize and validate a Phase 0 hardware probe JSON file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qpnpu.config import load_json  # noqa: E402
from qpnpu.probe_schema import validate_probe_result  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("probe", help="Path to a probe JSON file.")
    args = parser.parse_args(argv)

    probe = load_json(args.probe)
    errors = validate_probe_result(probe)
    if errors:
        print("probe validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    print(f"schema version: {probe.get('schema_version')}")
    print(f"source: {probe.get('source')}")
    _print_summary("device", probe.get("device", {}))
    _print_summary("cpu", probe.get("cpu", {}))
    _print_summary("memory", probe.get("memory", {}))
    _print_summary("npu", probe.get("npu", {}))

    warnings = probe.get("warnings", [])
    print("warnings:")
    if warnings:
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("  - none")

    print("recommended backend order:")
    for backend in _recommended_backends(probe):
        print(f"  - {backend}")
    return 0


def _print_summary(name: str, value: Any) -> None:
    if not isinstance(value, dict) or not value:
        print(f"{name}: <empty>")
        return
    print(f"{name}: {json.dumps(value, sort_keys=True)}")


def _recommended_backends(probe: dict[str, Any]) -> list[str]:
    backends: list[str] = []
    npu = probe.get("npu", {})
    gpu = probe.get("gpu", {})
    if _available(npu, "qnn"):
        backends.append("qnn")
    if _available(npu, "nnapi"):
        backends.append("nnapi")
    if _available(gpu, "vulkan"):
        backends.append("vulkan")
    backends.append("cpu")
    return backends


def _available(container: Any, feature: str) -> bool:
    if not isinstance(container, dict):
        return False
    direct_key = f"{feature}_available"
    if container.get(direct_key) is True:
        return True
    nested = container.get(feature)
    if isinstance(nested, dict) and nested.get("available") is True:
        return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())

