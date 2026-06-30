#!/usr/bin/env python
"""Verify Phase 2 Python and native checks when local tooling is available."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", default="native/build", help="Native CMake build directory.")
    parser.add_argument("--skip-native", action="store_true", help="Run Python tests only.")
    parser.add_argument("--config", default="Release", help="CMake build configuration for multi-config generators.")
    parser.add_argument("--verbose", action="store_true", help="Print command output as it runs.")
    args = parser.parse_args(argv)

    print_header("Phase 2 Verification")
    python_status = run_section(
        "Python tests",
        [sys.executable, "-m", "pytest", "tests"],
        verbose=args.verbose,
    )
    if python_status != 0:
        print_status("Python tests", "FAIL", "python -m pytest tests failed")
        return 1
    print_status("Python tests", "PASS", "python -m pytest tests")

    if args.skip_native:
        print_status("Native verification", "BLOCKED", "skipped by --skip-native")
        return 0

    cmake = shutil.which("cmake")
    if cmake is None:
        print_status("Native verification", "BLOCKED", "cmake was not found on PATH")
        print_path_hints()
        return 2

    compiler = first_available(["cl", "g++", "clang++", "c++"])
    if compiler is None:
        print_status(
            "Compiler probe",
            "BLOCKED",
            "no cl, g++, clang++, or c++ executable was found on PATH; trying CMake discovery anyway",
        )
    else:
        print_status("Compiler probe", "PASS", f"found {compiler}")

    build_dir = Path(args.build_dir)
    configure = run_section(
        "CMake configure",
        [cmake, "-S", "native", "-B", str(build_dir)],
        verbose=args.verbose,
    )
    if configure != 0:
        if compiler is None:
            print_status("CMake configure", "BLOCKED", "CMake could not configure; likely missing C++ toolchain")
            print_path_hints()
            return 2
        print_status("CMake configure", "FAIL", "cmake configure failed")
        return 1
    print_status("CMake configure", "PASS", str(build_dir))

    build = run_section(
        "CMake build",
        [cmake, "--build", str(build_dir), "--config", args.config],
        verbose=args.verbose,
    )
    if build != 0:
        print_status("CMake build", "FAIL", "native build failed")
        return 1
    print_status("CMake build", "PASS", args.config)

    ctest = shutil.which("ctest")
    if ctest is None:
        print_status("CTest", "BLOCKED", "ctest was not found on PATH")
        return 2
    native_tests = run_section(
        "CTest",
        [ctest, "--test-dir", str(build_dir), "--build-config", args.config, "--output-on-failure"],
        verbose=args.verbose,
    )
    if native_tests != 0:
        print_status("CTest", "FAIL", "native tests failed")
        return 1
    print_status("CTest", "PASS", "native tests")

    microbench = find_microbench(build_dir)
    if microbench is None:
        print_status("Microbench smoke", "BLOCKED", "qpnpu_microbench executable was not found after build")
        return 2

    smoke_out = Path("benchmarks/results/local_int4_smoke.json")
    smoke = run_section(
        "Microbench smoke",
        [
            str(microbench),
            "--operator",
            "int4_matvec",
            "--rows",
            "16",
            "--cols",
            "16",
            "--group-size",
            "8",
            "--iters",
            "5",
            "--out",
            str(smoke_out),
        ],
        verbose=args.verbose,
    )
    if smoke != 0:
        print_status("Microbench smoke", "FAIL", "native microbench smoke failed")
        return 1
    print_status("Microbench smoke", "PASS", str(smoke_out))

    wrapper = run_section(
        "Python microbench wrapper",
        [
            sys.executable,
            "scripts/native/run_local_microbench.py",
            "--build-dir",
            str(build_dir),
            "--out",
            "benchmarks/results/local_microbench.json",
        ],
        verbose=args.verbose,
    )
    if wrapper != 0:
        print_status("Python microbench wrapper", "FAIL", "wrapper failed")
        return 1
    print_status("Python microbench wrapper", "PASS", "benchmarks/results/local_microbench.json")

    print_status("Phase 2", "PASS", "Python and native verification completed locally")
    return 0


def run_section(name: str, command: list[str], *, verbose: bool) -> int:
    print_header(name)
    print("$ " + " ".join(command))
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=None if verbose else subprocess.PIPE,
        stderr=None if verbose else subprocess.STDOUT,
        check=False,
    )
    if not verbose and completed.stdout:
        print(completed.stdout.rstrip())
    return completed.returncode


def first_available(names: list[str]) -> str | None:
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def find_microbench(build_dir: Path) -> Path | None:
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


def print_header(title: str) -> None:
    print()
    print(f"== {title} ==")


def print_status(name: str, status: str, detail: str) -> None:
    print(f"{status}: {name} - {detail}")


def print_path_hints() -> None:
    print("Install hints:")
    print("  Windows: install CMake and Visual Studio Build Tools with C++ workload.")
    print("  Linux: install cmake and a compiler package such as build-essential.")
    print("  macOS: install Xcode Command Line Tools and CMake.")
    print("This verifier never requires Android, AWS, QNN, or network access.")


if __name__ == "__main__":
    raise SystemExit(main())

