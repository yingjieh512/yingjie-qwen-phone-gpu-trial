#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 [output-json]"
  echo
  echo "Phase 0 stub. Future phases will collect Android device info through adb."
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if ! command -v adb >/dev/null 2>&1; then
  echo "error: adb was not found on PATH. Install Android platform-tools for future probe work." >&2
  exit 127
fi

OUTPUT="${1:-benchmarks/results/latest_probe.json}"
echo "Phase 0 stub: would collect device info and write ${OUTPUT}"
echo "Intended checks: adb devices, getprop, thermal state, CPU, memory, GPU, NNAPI, and QNN hints."

