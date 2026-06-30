#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 [--out DIR]"
  echo
  echo "Collect a Phase 1 host-side Android hardware probe with adb shell commands."
  echo
  echo "Options:"
  echo "  --out DIR   Output directory. Defaults to benchmarks/results/<utc-timestamp>."
  echo "  -h, --help  Show this help."
  echo
  echo "Environment:"
  echo "  ANDROID_SERIAL may be set to select a specific adb device."
}

OUT_DIR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      if [[ $# -lt 2 ]]; then
        echo "error: --out requires a directory argument" >&2
        exit 2
      fi
      OUT_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! command -v adb >/dev/null 2>&1; then
  echo "error: adb was not found on PATH. Install Android platform-tools and retry." >&2
  exit 127
fi

ADB=(adb)
if [[ -n "${ANDROID_SERIAL:-}" ]]; then
  ADB+=(-s "${ANDROID_SERIAL}")
fi

if ! DEVICE_STATE="$("${ADB[@]}" get-state 2>&1)"; then
  echo "error: adb is installed, but no usable Android device is connected." >&2
  echo "${DEVICE_STATE}" >&2
  echo "Run 'adb devices' and set ANDROID_SERIAL if multiple devices are connected." >&2
  exit 2
fi

if [[ "${DEVICE_STATE}" != "device" ]]; then
  echo "error: adb device state is '${DEVICE_STATE}', expected 'device'." >&2
  echo "Unlock the device, accept USB debugging, then retry." >&2
  exit 2
fi

if [[ -z "${OUT_DIR}" ]]; then
  TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
  OUT_DIR="benchmarks/results/${TIMESTAMP}"
fi

mkdir -p "${OUT_DIR}"

run_shell_file() {
  local output_file="$1"
  local command="$2"
  {
    echo "$ adb shell ${command}"
    if ! "${ADB[@]}" shell "${command}"; then
      local status=$?
      echo "ERROR: adb shell command failed with exit code ${status}"
    fi
  } > "${OUT_DIR}/${output_file}" 2>&1
}

echo "Collecting ADB hardware probe into ${OUT_DIR}"
run_shell_file raw_getprop.txt "getprop"
run_shell_file raw_uname.txt "uname -a"
run_shell_file raw_cpuinfo.txt "cat /proc/cpuinfo"
run_shell_file raw_meminfo.txt "cat /proc/meminfo"
run_shell_file raw_sysfs_cpu.txt 'for path in /sys/devices/system/cpu/possible /sys/devices/system/cpu/present /sys/devices/system/cpu/online /sys/devices/system/cpu/cpu*/cpufreq/cpuinfo_max_freq /sys/devices/system/cpu/cpu*/cpufreq/cpuinfo_min_freq /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor /sys/devices/system/cpu/cpu*/topology/physical_package_id /sys/devices/system/cpu/cpu*/topology/core_id /sys/devices/system/cpu/cpu*/topology/cluster_id /sys/devices/system/cpu/cpu*/topology/cpu_capacity; do echo "### ${path}"; cat "${path}" 2>&1 || true; done'
run_shell_file raw_thermal.txt 'for path in /sys/class/thermal/thermal_zone*/type /sys/class/thermal/thermal_zone*/temp /sys/class/thermal/cooling_device*/type /sys/class/thermal/cooling_device*/cur_state /sys/class/thermal/cooling_device*/max_state; do echo "### ${path}"; cat "${path}" 2>&1 || true; done'
run_shell_file raw_gpu.txt 'echo "### getprop filtered"; getprop | grep -Ei "gpu|egl|vulkan|renderer|ro.hardware|ro.board|ro.soc|vendor|qualcomm|qti" || true; for dir in /vendor/lib64 /system/lib64 /apex; do echo "### ls ${dir}"; ls -la "${dir}" 2>&1 || true; done; echo "### library hints"; find /vendor/lib64 /system/lib64 /apex -maxdepth 3 2>&1 | grep -Ei "vulkan|OpenCL|GLES|Adreno|kgsl" || true'
run_shell_file raw_npu.txt 'echo "### getprop filtered"; getprop | grep -Ei "npu|dsp|htp|hexagon|neural|nnapi|qnn|qti|qualcomm|ai" || true; for dir in /vendor/lib64 /system/lib64 /odm/lib64; do echo "### ls ${dir}"; ls -la "${dir}" 2>&1 || true; done; echo "### library hints"; find /vendor/lib64 /system/lib64 /odm/lib64 -maxdepth 3 2>&1 | grep -Ei "libQnnHtp.so|libQnnSystem.so|libQnnCpu.so|libQnnGpu.so|libQnnDsp.so|libcdsprpc.so|libhta.so|libhexagon_nn|nnapi" || true'

python scripts/adb/build_probe_json.py --raw-dir "${OUT_DIR}" --out "${OUT_DIR}/probe_result.json"
cp "${OUT_DIR}/probe_result.json" benchmarks/results/latest_probe.json

echo "Wrote ${OUT_DIR}/probe_result.json"
echo "Updated benchmarks/results/latest_probe.json"