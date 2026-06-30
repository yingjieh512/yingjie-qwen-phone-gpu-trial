#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 [package-name]"
  echo
  echo "Phase 1 placeholder. Host-side probing is implemented, but benchmarks are not run in Phase 1."
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if ! command -v adb >/dev/null 2>&1; then
  echo "error: adb was not found on PATH. Install Android platform-tools for future benchmark work." >&2
  exit 127
fi

PACKAGE="${1:-com.qpnpu.trial}"
echo "Phase 1 placeholder: would run benchmark package ${PACKAGE} in a later phase."
echo "No benchmark APK or native benchmark runner exists in Phase 1."