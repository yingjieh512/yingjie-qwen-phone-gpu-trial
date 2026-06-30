#!/usr/bin/env python
"""Generate a tiny placeholder C++ kernel file from a Phase 0 config."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qpnpu.config import load_json, utc_now_iso  # noqa: E402
from qpnpu.kernel_config import kernel_config_hash, validate_kernel_config  # noqa: E402
from qpnpu.model_format import validate_model_metadata  # noqa: E402
from qpnpu.probe_schema import validate_probe_result  # noqa: E402


GENERATOR_VERSION = "0.1"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", help="Optional probe JSON used for future capability-aware generation.")
    parser.add_argument("--config", required=True, help="Kernel config JSON.")
    parser.add_argument("--model-metadata", help="Optional QPNPU model metadata JSON.")
    parser.add_argument("--out", required=True, help="Output directory for generated placeholder C++.")
    args = parser.parse_args(argv)

    if args.probe:
        probe = load_json(args.probe)
        errors = validate_probe_result(probe)
        if errors:
            print("probe validation failed:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 2

    if args.model_metadata:
        metadata = load_json(args.model_metadata)
        errors = validate_model_metadata(metadata)
        if errors:
            print("model metadata validation failed:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 2

    config = load_json(args.config)
    errors = validate_kernel_config(config)
    if errors:
        print("kernel config validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    config_hash = kernel_config_hash(config)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"generated_int4_matvec_{config_hash}.cpp"
    output_path.write_text(_render_placeholder(config, config_hash), encoding="utf-8")

    print(f"generated placeholder kernel: {output_path}")
    print(f"config hash: {config_hash}")
    return 0


def _render_placeholder(config: dict, config_hash: str) -> str:
    config_json = json.dumps(config, sort_keys=True, indent=2)
    return f"""// qpnpu generated kernel placeholder
// generator version: {GENERATOR_VERSION}
// timestamp UTC: {utc_now_iso()}
// config hash: {config_hash}
// DO NOT EDIT MANUALLY

#include <cstddef>

namespace qpnpu {{

// Phase 0 placeholder generated from:
/*
{config_json}
*/
int generated_int4_matvec_{config_hash}(const void*, const void*, void*, std::size_t) {{
    return 0;
}}

}}  // namespace qpnpu
"""


if __name__ == "__main__":
    raise SystemExit(main())

