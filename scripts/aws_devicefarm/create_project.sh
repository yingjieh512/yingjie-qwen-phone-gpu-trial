#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: AWS_REGION=us-west-2 PROJECT_NAME=qpnpu-trial $0"
  echo
  echo "Required env vars in a later phase: AWS_REGION, PROJECT_NAME"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "error: aws CLI was not found on PATH. Configure AWS CLI in a later Device Farm phase." >&2
  usage >&2
  exit 127
fi

AWS_REGION="${AWS_REGION:-us-west-2}"
PROJECT_NAME="${PROJECT_NAME:-qpnpu-trial}"
usage
echo "Phase 0 stub: no project is created."
echo "Intended command:"
echo "aws devicefarm create-project --region ${AWS_REGION} --name ${PROJECT_NAME}"

