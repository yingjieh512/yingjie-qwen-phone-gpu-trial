#!/usr/bin/env python
"""Find the most likely QPNPU Probe debug APK."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def find_debug_apks(root: Path) -> list[Path]:
    """Return debug APK candidates under ``android/probe-app``."""

    project_dir = root / "android" / "probe-app"
    if not project_dir.exists():
        return []
    candidates = [
        path
        for path in project_dir.rglob("*.apk")
        if path.is_file() and "debug" in path.name.lower()
    ]
    return sorted(candidates, key=lambda path: (_score(path), path.stat().st_mtime), reverse=True)


def select_best_apk(root: Path) -> Path | None:
    """Select the most likely debug APK path, if any."""

    candidates = find_debug_apks(root)
    return candidates[0] if candidates else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="Repository root to search. Defaults to this script's repository.",
    )
    args = parser.parse_args(argv)

    apk = select_best_apk(args.root)
    if apk is None:
        print("error: no debug APK found under android/probe-app", file=sys.stderr)
        print("build it first with: cd android/probe-app && ./gradlew assembleDebug", file=sys.stderr)
        return 2
    print(apk)
    return 0


def _score(path: Path) -> int:
    normalized = "/".join(part.lower() for part in path.parts)
    score = 0
    if normalized.endswith("/app/build/outputs/apk/debug/app-debug.apk"):
        score += 100
    if "/build/outputs/apk/" in normalized:
        score += 30
    if path.name.lower() == "app-debug.apk":
        score += 20
    if path.name.lower().endswith("-debug.apk"):
        score += 10
    return score


if __name__ == "__main__":
    raise SystemExit(main())
