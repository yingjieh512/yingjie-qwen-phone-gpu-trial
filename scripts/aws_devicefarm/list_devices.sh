#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: AWS_REGION=us-west-2 $0"
  echo
  echo "Lists intended Samsung Android Device Farm devices in a later phase."
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
echo "Phase 0 stub: no AWS request is made by this script yet."
echo "Intended command for Samsung Android devices:"
echo "aws devicefarm list-devices --region ${AWS_REGION} --filters '[{\"attribute\":\"PLATFORM\",\"operator\":\"EQUALS\",\"values\":[\"ANDROID\"]},{\"attribute\":\"MANUFACTURER\",\"operator\":\"EQUALS\",\"values\":[\"SAMSUNG\"]}]'"

