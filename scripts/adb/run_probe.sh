#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 [package-name]"
  echo
  echo "Phase 0 stub. Future phases will run a minimal Android probe APK or test runner."
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if ! command -v adb >/dev/null 2>&1; then
  echo "error: adb was not found on PATH. Install Android platform-tools for future probe work." >&2
  exit 127
fi

PACKAGE="${1:-com.qpnpu.trial}"
echo "Phase 0 stub: would run probe package ${PACKAGE}"
echo "No APK exists in Phase 0."

