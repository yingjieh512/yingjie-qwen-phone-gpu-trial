#!/usr/bin/env python
"""Extract QPNPU probe, native benchmark, Phase 6, Phase 7A, toy decode, or bundled JSON from AWS Device Farm logcat text."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qpnpu.android_logcat import (  # noqa: E402
    write_all_qpnpu_json_from_logcat,
    write_extracted_android_toy_decode_json,
    write_extracted_phase6_characterization_json,
    write_extracted_phase7a_isa_probes_json,
    write_extracted_native_benchmark_json,
    write_extracted_probe_json,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logcat", required=True, help="Downloaded or pasted logcat text file.")
    parser.add_argument("--out", required=True, help="Clean JSON output path.")
    parser.add_argument(
        "--kind",
        choices=["probe", "native", "phase6", "phase7a", "toy_decode", "all"],
        default="probe",
        help="Which QPNPU marker pair to extract, or all for a bundled artifact. Default: probe.",
    )
    args = parser.parse_args(argv)

    try:
        if args.kind == "native":
            out = write_extracted_native_benchmark_json(args.logcat, args.out)
        elif args.kind == "phase6":
            out = write_extracted_phase6_characterization_json(args.logcat, args.out)
        elif args.kind == "phase7a":
            out = write_extracted_phase7a_isa_probes_json(args.logcat, args.out)
        elif args.kind == "toy_decode":
            out = write_extracted_android_toy_decode_json(args.logcat, args.out)
        elif args.kind == "all":
            out = write_all_qpnpu_json_from_logcat(args.logcat, args.out)
        else:
            out = write_extracted_probe_json(args.logcat, args.out)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote extracted {args.kind} JSON: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
