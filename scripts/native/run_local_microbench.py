#!/usr/bin/env python
"""Run Phase 2 local CPU native microbenchmarks and combine their JSON results."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qpnpu.benchmark import validate_benchmark_result  # noqa: E402


BENCHMARKS = [
    ("int4_matvec", ["--rows", "256", "--cols", "256", "--group-size", "128"]),
    ("rmsnorm", ["--n", "4096"]),
    ("rope", ["--n", "128"]),
    ("softmax", ["--n", "4096"]),
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", default="native/build", help="CMake build directory containing qpnpu_microbench.")
    parser.add_argument("--exe", help="Explicit qpnpu_microbench executable path.")
    parser.add_argument("--out", default="benchmarks/results/local_microbench.json", help="Combined JSON list output path.")
    parser.add_argument("--iters", type=int, default=10, help="Iterations per operator benchmark.")
    args = parser.parse_args(argv)

    build_dir = Path(args.build_dir)
    executable = _find_microbench(build_dir, Path(args.exe) if args.exe else None)
    if executable is None:
        print(f"error: qpnpu_microbench executable was not found under {build_dir}", file=sys.stderr)
        if args.exe:
            print(f"explicit --exe path did not exist or was not a file: {args.exe}", file=sys.stderr)
        print("build it first with:", file=sys.stderr)
        print("  cmake -S native -B native/build", file=sys.stderr)
        print("  cmake --build native/build --config Release", file=sys.stderr)
        return 2

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for operator, operator_args in BENCHMARKS:
        per_op_out = out_path.with_name(f"{out_path.stem}_{operator}{out_path.suffix}")
        command = [
            str(executable),
            "--operator",
            operator,
            "--iters",
            str(args.iters),
            *operator_args,
            "--out",
            str(per_op_out),
        ]
        print("running:", " ".join(command))
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        if completed.returncode != 0:
            return completed.returncode

        result = json.loads(per_op_out.read_text(encoding="utf-8"))
        errors = validate_benchmark_result(result)
        if errors:
            print(f"error: invalid benchmark JSON from {operator}:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 2
        results.append(result)

    out_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote combined local CPU microbenchmarks: {out_path}")
    print("warning: local CPU microbenchmarks are not phone or NPU performance claims")
    return 0


def _find_microbench(build_dir: Path, explicit_exe: Path | None) -> Path | None:
    if explicit_exe is not None:
        return explicit_exe if explicit_exe.exists() and explicit_exe.is_file() else None

    candidates = [
        build_dir / "qpnpu_microbench",
        build_dir / "qpnpu_microbench.exe",
        build_dir / "Debug" / "qpnpu_microbench.exe",
        build_dir / "Release" / "qpnpu_microbench.exe",
        build_dir / "RelWithDebInfo" / "qpnpu_microbench.exe",
        build_dir / "MinSizeRel" / "qpnpu_microbench.exe",
        build_dir / "tools" / "qpnpu_microbench",
        build_dir / "tools" / "qpnpu_microbench.exe",
        build_dir / "tools" / "Debug" / "qpnpu_microbench.exe",
        build_dir / "tools" / "Release" / "qpnpu_microbench.exe",
        build_dir / "tools" / "RelWithDebInfo" / "qpnpu_microbench.exe",
        build_dir / "tools" / "MinSizeRel" / "qpnpu_microbench.exe",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


if __name__ == "__main__":
    raise SystemExit(main())