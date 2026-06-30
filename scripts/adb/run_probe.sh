#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 [--out DIR]"
  echo
  echo "Phase 1 host-side probe wrapper. Delegates to collect_device_info.sh."
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/collect_device_info.sh" "$@"