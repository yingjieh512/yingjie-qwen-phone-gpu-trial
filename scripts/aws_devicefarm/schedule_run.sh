#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: AWS_REGION=us-west-2 PROJECT_ARN=... DEVICE_POOL_ARN=... APP_ARN=... TEST_PACKAGE_ARN=... $0"
  echo
  echo "Required env vars in a later phase: AWS_REGION, PROJECT_ARN, DEVICE_POOL_ARN, APP_ARN, TEST_PACKAGE_ARN"
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
PROJECT_ARN="${PROJECT_ARN:-<project-arn>}"
DEVICE_POOL_ARN="${DEVICE_POOL_ARN:-<device-pool-arn>}"
APP_ARN="${APP_ARN:-<app-upload-arn>}"
TEST_PACKAGE_ARN="${TEST_PACKAGE_ARN:-<test-package-upload-arn>}"
usage
echo "Phase 0 stub: no Device Farm run is scheduled."
echo "Intended command:"
echo "aws devicefarm schedule-run --region ${AWS_REGION} --project-arn ${PROJECT_ARN} --device-pool-arn ${DEVICE_POOL_ARN} --app-arn ${APP_ARN} --test '{\"type\":\"INSTRUMENTATION\",\"testPackageArn\":\"'${TEST_PACKAGE_ARN}'\"}'"

