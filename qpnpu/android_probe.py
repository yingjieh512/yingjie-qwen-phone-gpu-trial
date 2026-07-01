"""Summarize Android-side QPNPU probe JSON results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from qpnpu.probe_schema import validate_probe_result


def read_android_probe(path: str | Path) -> dict[str, Any]:
    """Read an Android probe JSON file and validate the common probe schema."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    errors = validate_probe_result(data)
    if errors:
        joined = "; ".join(errors)
        raise ValueError(f"invalid Android probe JSON: {joined}")
    return data


def summarize_android_probe(data: dict[str, Any]) -> dict[str, Any]:
    """Return a compact, conservative summary of Android probe capabilities."""

    errors = validate_probe_result(data)
    if errors:
        joined = "; ".join(errors)
        raise ValueError(f"invalid Android probe JSON: {joined}")

    device = _object(data.get("device"))
    cpu = _object(data.get("cpu"))
    memory = _object(data.get("memory"))
    gpu = _object(data.get("gpu"))
    npu = _object(data.get("npu"))
    thermal = _object(data.get("thermal"))

    gpu_hints = _strings(gpu.get("library_hints")) + _strings(gpu.get("shell_hints")) + _strings(gpu.get("direct_library_hints"))
    npu_hints = _strings(npu.get("library_hints")) + _strings(npu.get("shell_hints")) + _strings(npu.get("direct_library_hints"))
    thermal_zones = _list(thermal.get("zones"))

    summary = {
        "schema_version": "0.1",
        "source_probe": {
            "source": data.get("source", ""),
            "timestamp_utc": data.get("timestamp_utc", ""),
        },
        "device": {
            "manufacturer": device.get("manufacturer", ""),
            "model": device.get("model", ""),
            "device": device.get("device", ""),
            "board": device.get("board", ""),
            "hardware": device.get("hardware", ""),
            "soc_manufacturer": device.get("soc_manufacturer", ""),
            "soc_model": device.get("soc_model", ""),
            "android_release": device.get("android_release", ""),
            "sdk_version": device.get("sdk_version", ""),
            "supported_abis": _strings(device.get("supported_abis")),
        },
        "cpu": {
            "available_processors": cpu.get("available_processors"),
            "proc_cpuinfo_readable": bool(cpu.get("proc_cpuinfo_readable")),
            "feature_summary": _cpu_feature_summary(str(cpu.get("proc_cpuinfo_excerpt", ""))),
        },
        "memory": {
            "runtime_max_memory_bytes": memory.get("runtime_max_memory_bytes"),
            "mem_total_kb": _parse_meminfo_kb(str(memory.get("proc_meminfo_excerpt", "")), "MemTotal"),
            "mem_available_kb": _parse_meminfo_kb(str(memory.get("proc_meminfo_excerpt", "")), "MemAvailable"),
            "proc_meminfo_readable": bool(memory.get("proc_meminfo_readable")),
        },
        "gpu": {
            "status": gpu.get("status", "unknown"),
            "library_dirs_readable": bool(gpu.get("library_dirs_readable")),
            "vulkan_libraries_detected": bool(gpu.get("vulkan_libraries_detected")),
            "hint_count": len(gpu_hints),
            "notable_hints": _notable(gpu_hints, ["adreno", "opencl", "vulkan", "gles", "kgsl"]),
            "availability_claim": gpu.get("availability_claim", "none"),
        },
        "npu": {
            "status": npu.get("status", "unknown"),
            "library_dirs_readable": bool(npu.get("library_dirs_readable")),
            "qnn_libraries_detected": bool(npu.get("qnn_libraries_detected")),
            "nnapi_string_hints_detected": bool(npu.get("nnapi_string_hints_detected")),
            "hint_count": len(npu_hints),
            "notable_hints": _notable(npu_hints, ["qnn", "htp", "hexagon", "cdsp", "dsp", "snpe", "neuralnetworks"]),
            "availability_claim": npu.get("availability_claim", "none"),
        },
        "thermal": {
            "status": thermal.get("status", "unknown"),
            "zone_count": len(thermal_zones),
            "notable_zones": _notable(
                [str(_object(zone).get("type", "")) for zone in thermal_zones],
                ["cpu", "gpu", "kgsl", "cdsp", "ddr", "ufs"],
            ),
        },
        "warnings": _strings(data.get("warnings")),
        "interpretation": _interpretation(gpu, npu, thermal_zones),
    }
    return summary


def render_android_probe_summary(summary: dict[str, Any]) -> str:
    """Render a concise text summary for terminals and docs."""

    device = _object(summary.get("device"))
    cpu = _object(summary.get("cpu"))
    memory = _object(summary.get("memory"))
    gpu = _object(summary.get("gpu"))
    npu = _object(summary.get("npu"))
    thermal = _object(summary.get("thermal"))
    interpretation = _list(summary.get("interpretation"))

    lines = [
        "Android probe summary",
        f"device: {device.get('manufacturer', '')} {device.get('model', '')} ({device.get('device', '')})",
        f"soc: {device.get('soc_manufacturer', '')} {device.get('soc_model', '')}; hardware={device.get('hardware', '')}",
        f"android: {device.get('android_release', '')} sdk={device.get('sdk_version', '')}; abi={', '.join(_strings(device.get('supported_abis')))}",
        f"cpu: processors={cpu.get('available_processors')} features={', '.join(_strings(_object(cpu.get('feature_summary')).get('present')))}",
        f"memory: MemTotal={memory.get('mem_total_kb')} kB MemAvailable={memory.get('mem_available_kb')} kB",
        f"gpu: status={gpu.get('status')} vulkan_libraries_detected={gpu.get('vulkan_libraries_detected')} hints={gpu.get('hint_count')}",
        f"npu: status={npu.get('status')} qnn_libraries_detected={npu.get('qnn_libraries_detected')} hints={npu.get('hint_count')}",
        f"thermal: status={thermal.get('status')} zones={thermal.get('zone_count')}",
        "interpretation:",
    ]
    lines.extend(f"- {item}" for item in interpretation)
    return "\n".join(lines)


def write_summary_json(path: str | Path, summary: dict[str, Any]) -> Path:
    """Write a summary JSON file."""

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def write_summary_markdown(path: str | Path, summary: dict[str, Any]) -> Path:
    """Write a small markdown hardware profile from a summary object."""

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    device = _object(summary.get("device"))
    cpu = _object(summary.get("cpu"))
    memory = _object(summary.get("memory"))
    gpu = _object(summary.get("gpu"))
    npu = _object(summary.get("npu"))
    thermal = _object(summary.get("thermal"))

    text = f"""# Target Hardware Profile

Generated from Android probe source `{_object(summary.get("source_probe")).get("source", "")}` at `{_object(summary.get("source_probe")).get("timestamp_utc", "")}`.

## Device

- Manufacturer: {device.get("manufacturer", "")}
- Model: {device.get("model", "")}
- Device: {device.get("device", "")}
- Board: {device.get("board", "")}
- Hardware: {device.get("hardware", "")}
- SoC: {device.get("soc_manufacturer", "")} {device.get("soc_model", "")}
- Android: {device.get("android_release", "")} / SDK {device.get("sdk_version", "")}
- ABIs: {", ".join(_strings(device.get("supported_abis")))}

## CPU And Memory

- Available processors: {cpu.get("available_processors")}
- CPU info readable: {cpu.get("proc_cpuinfo_readable")}
- Feature flags present: {", ".join(_strings(_object(cpu.get("feature_summary")).get("present")))}
- MemTotal: {memory.get("mem_total_kb")} kB
- MemAvailable: {memory.get("mem_available_kb")} kB
- Runtime max memory: {memory.get("runtime_max_memory_bytes")} bytes

## GPU Hints

- Status: {gpu.get("status")}
- Vulkan libraries detected: {gpu.get("vulkan_libraries_detected")}
- Hint count: {gpu.get("hint_count")}
- Notable hints: {", ".join(_strings(gpu.get("notable_hints")))}
- Availability claim: {gpu.get("availability_claim")}

## NPU/DSP Hints

- Status: {npu.get("status")}
- QNN libraries detected: {npu.get("qnn_libraries_detected")}
- NNAPI string hints detected: {npu.get("nnapi_string_hints_detected")}
- Hint count: {npu.get("hint_count")}
- Notable hints: {", ".join(_strings(npu.get("notable_hints")))}
- Availability claim: {npu.get("availability_claim")}

## Thermal

- Status: {thermal.get("status")}
- Zone count: {thermal.get("zone_count")}
- Notable zones: {", ".join(_strings(thermal.get("notable_zones")))}

## Interpretation

{chr(10).join(f"- {item}" for item in _strings(summary.get("interpretation")))}

This profile is hardware discovery evidence only. It is not a performance result and does not prove QNN, NPU, Vulkan, or NNAPI execution.
"""
    out.write_text(text, encoding="utf-8")
    return out


def _interpretation(gpu: dict[str, Any], npu: dict[str, Any], thermal_zones: list[Any]) -> list[str]:
    notes = [
        "CPU fallback should be treated as mandatory; the probe confirms app-side execution and readable CPU/memory data.",
    ]
    if npu.get("qnn_libraries_detected"):
        notes.append("QNN library names were detected; a later phase should test controlled dlopen/API access before claiming usability.")
    elif npu.get("status") == "hints_detected":
        notes.append("NPU/DSP string hints were detected, but no QNN library availability was proven by this probe.")
    else:
        notes.append("No NPU/DSP hints were detected by this probe.")

    if gpu.get("vulkan_libraries_detected"):
        notes.append("Vulkan library names were detected; a later phase should make real Vulkan API calls.")
    elif gpu.get("status") == "hints_detected":
        notes.append("GPU/OpenCL/GLES hints were detected, but Vulkan was not proven by this probe.")
    else:
        notes.append("No GPU library hints were detected by this probe.")

    if thermal_zones:
        notes.append("Thermal/cooling entries were readable, so future benchmark JSON should capture thermal state.")
    else:
        notes.append("Thermal/cooling entries were not readable; future benchmarks may need alternate thermal telemetry.")
    return notes


def _parse_meminfo_kb(text: str, key: str) -> int | None:
    prefix = f"{key}:"
    for line in text.splitlines():
        if line.startswith(prefix):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    return int(parts[1])
                except ValueError:
                    return None
    return None


def _cpu_feature_summary(cpuinfo: str) -> dict[str, list[str]]:
    interesting = ["asimddp", "i8mm", "bf16", "sve", "sve2", "svei8mm", "sme", "sha3"]
    lower = cpuinfo.lower()
    present = [feature for feature in interesting if feature in lower]
    missing = [feature for feature in interesting if feature not in lower]
    return {"present": present, "missing": missing}


def _notable(values: list[str], needles: list[str], limit: int = 24) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        lower = value.lower()
        if any(needle in lower for needle in needles) and value not in seen:
            result.append(value)
            seen.add(value)
        if len(result) >= limit:
            break
    return result


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]
