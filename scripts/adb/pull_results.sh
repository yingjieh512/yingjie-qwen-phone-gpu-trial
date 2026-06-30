#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 [remote-dir] [local-dir]"
  echo
  echo "Phase 0 stub. Future phases will pull JSON probe and benchmark results from Android."
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if ! command -v adb >/dev/null 2>&1; then
  echo "error: adb was not found on PATH. Install Android platform-tools for future result collection." >&2
  exit 127
fi

REMOTE="${1:-/sdcard/Android/data/com.qpnpu.trial/files/results}"
LOCAL="${2:-benchmarks/results}"
echo "Phase 0 stub: would pull ${REMOTE} to ${LOCAL}"

