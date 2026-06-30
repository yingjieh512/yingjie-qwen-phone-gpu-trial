#!/usr/bin/env python
"""Summarize and validate a hardware probe JSON file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qpnpu.adb_probe import recommended_backend_order  # noqa: E402
from qpnpu.config import load_json  # noqa: E402
from qpnpu.probe_schema import validate_probe_result  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("probe", help="Path to a probe JSON file.")
    args = parser.parse_args(argv)

    probe = load_json(args.probe)
    errors = validate_probe_result(probe)
    if errors:
        print("probe validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    device = _as_dict(probe.get("device"))
    cpu = _as_dict(probe.get("cpu"))
    memory = _as_dict(probe.get("memory"))
    thermal = _as_dict(probe.get("thermal"))
    gpu = _as_dict(probe.get("gpu"))
    npu = _as_dict(probe.get("npu"))

    print(f"schema version: {probe.get('schema_version')}")
    print(f"timestamp: {probe.get('timestamp_utc')}")
    print(f"source: {probe.get('source')}")
    print(f"device: {_device_summary(device)}")
    print(f"android: {_android_summary(device)}")
    print(f"soc: {_soc_summary(device)}")
    print(f"cpu cores: {cpu.get('processor_count', '<unknown>')}")
    print(f"cpu max frequencies: {_cpu_freq_summary(cpu)}")
    print(f"memory: {_memory_summary(memory)}")
    print(f"thermal zones: {len(thermal.get('thermal_zones', []))}")
    print(f"gpu hints: {_gpu_summary(gpu)}")
    print(f"npu hints: {_npu_summary(npu)}")

    warnings = probe.get("warnings", [])
    print("warnings:")
    if warnings:
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("  - none")

    backends = recommended_backend_order(probe)
    print("recommended backend order:")
    for backend in backends:
        print(f"  - {backend}")
    if backends == ["cpu"]:
        print("warning: no accelerator library hints detected; only CPU is currently recommended.")
    return 0


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _device_summary(device: dict[str, Any]) -> str:
    manufacturer = device.get("manufacturer", "<unknown manufacturer>")
    model = device.get("model", "<unknown model>")
    return f"{manufacturer} {model}"


def _android_summary(device: dict[str, Any]) -> str:
    release = device.get("android_release", "<unknown>")
    sdk = device.get("sdk", "<unknown>")
    return f"release={release}, sdk={sdk}"


def _soc_summary(device: dict[str, Any]) -> str:
    manufacturer = device.get("soc_manufacturer", "<unknown>")
    model = device.get("soc_model", "<unknown>")
    hardware = device.get("hardware", device.get("board", "<unknown>"))
    return f"manufacturer={manufacturer}, model={model}, hardware={hardware}"


def _cpu_freq_summary(cpu: dict[str, Any]) -> str:
    sysfs = _as_dict(cpu.get("sysfs"))
    per_core = _as_dict(sysfs.get("per_core_freqs"))
    max_freqs = []
    for values in per_core.values():
        if isinstance(values, dict) and values.get("cpuinfo_max_freq_khz") is not None:
            max_freqs.append(values["cpuinfo_max_freq_khz"])
    if not max_freqs:
        return "<unknown>"
    unique = sorted(set(max_freqs))
    return ", ".join(f"{freq} kHz" for freq in unique)


def _memory_summary(memory: dict[str, Any]) -> str:
    total = memory.get("mem_total_kb")
    available = memory.get("mem_available_kb")
    if total is None and available is None:
        return "<unknown>"
    return f"total={total} kB, available={available} kB"


def _gpu_summary(gpu: dict[str, Any]) -> str:
    return json.dumps(
        {
            "vulkan_libraries_detected": gpu.get("vulkan_libraries_detected", False),
            "opencl_libraries_detected": gpu.get("opencl_libraries_detected", False),
            "gles_libraries_detected": gpu.get("gles_libraries_detected", False),
            "adreno_hint_count": len(gpu.get("adreno_hints", [])),
        },
        sort_keys=True,
    )


def _npu_summary(npu: dict[str, Any]) -> str:
    return json.dumps(
        {
            "status": npu.get("status", "unknown"),
            "qnn_libraries_detected": npu.get("qnn_libraries_detected", False),
            "qnn_libraries": npu.get("qnn_libraries", []),
            "nnapi_hint_count": len(npu.get("nnapi_hints", [])),
            "hexagon_dsp_hint_count": len(npu.get("hexagon_dsp_hints", [])),
            "htp_hint_count": len(npu.get("htp_hints", [])),
        },
        sort_keys=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())