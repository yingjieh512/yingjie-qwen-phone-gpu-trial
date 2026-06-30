"""Host-side ADB probe parsing for Phase 1."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from qpnpu.config import utc_now_iso
from qpnpu.probe_schema import validate_probe_result


RAW_FILES = {
    "getprop": "raw_getprop.txt",
    "uname": "raw_uname.txt",
    "cpuinfo": "raw_cpuinfo.txt",
    "meminfo": "raw_meminfo.txt",
    "thermal": "raw_thermal.txt",
    "sysfs_cpu": "raw_sysfs_cpu.txt",
    "gpu": "raw_gpu.txt",
    "npu": "raw_npu.txt",
}

GETPROP_RE = re.compile(r"^\[([^\]]+)\]: \[(.*)\]\s*$")
CPU_ID_RE = re.compile(r"^processor\s*:\s*(\d+)\s*$", re.IGNORECASE | re.MULTILINE)
MEMINFO_RE = re.compile(r"^([A-Za-z_()]+):\s+(\d+)(?:\s+kB)?", re.MULTILINE)
QNN_LIB_RE = re.compile(r"libQnn[A-Za-z0-9_]*\.so", re.IGNORECASE)


def parse_getprop(text: str) -> dict[str, Any]:
    """Parse Android `getprop` output into selected device identity fields."""

    properties: dict[str, str] = {}
    for line in text.splitlines():
        match = GETPROP_RE.match(line.strip())
        if match:
            properties[match.group(1)] = match.group(2)

    result: dict[str, Any] = {
        "properties": properties,
        "property_count": len(properties),
    }
    _set_if_present(result, "manufacturer", _first(properties, [
        "ro.product.manufacturer",
        "ro.product.vendor.manufacturer",
        "ro.product.system.manufacturer",
    ]))
    _set_if_present(result, "model", _first(properties, [
        "ro.product.model",
        "ro.product.vendor.model",
        "ro.product.system.model",
    ]))
    _set_if_present(result, "device", _first(properties, ["ro.product.device", "ro.product.vendor.device"]))
    _set_if_present(result, "product", _first(properties, ["ro.product.name", "ro.product.vendor.name"]))
    _set_if_present(result, "board", _first(properties, [
        "ro.product.board",
        "ro.board.platform",
        "ro.boot.hardware.platform",
    ]))
    _set_if_present(result, "hardware", _first(properties, ["ro.hardware", "ro.boot.hardware"]))
    _set_if_present(result, "soc_manufacturer", _first(properties, [
        "ro.soc.manufacturer",
        "ro.vendor.soc.manufacturer",
        "ro.boot.soc.manufacturer",
    ]))
    _set_if_present(result, "soc_model", _first(properties, [
        "ro.soc.model",
        "ro.vendor.soc.model",
        "ro.board.platform",
        "ro.hardware.chipname",
        "ro.chipname",
    ]))
    _set_if_present(result, "android_release", _first(properties, ["ro.build.version.release"]))
    sdk = _parse_int(_first(properties, ["ro.build.version.sdk"]))
    if sdk is not None:
        result["sdk"] = sdk
    _set_if_present(result, "build_fingerprint", _first(properties, ["ro.build.fingerprint"]))
    supported_abis = _split_csv(_first(properties, ["ro.product.cpu.abilist", "ro.vendor.product.cpu.abilist"]))
    if supported_abis:
        result["supported_abis"] = supported_abis
    return result


def parse_uname(text: str) -> dict[str, Any]:
    """Parse `uname -a` output."""

    kernel = _strip_command_echo(text)
    if not kernel:
        return {"warnings": ["raw_uname.txt was empty"]}
    parts = kernel.split()
    result: dict[str, Any] = {"kernel": kernel}
    if parts:
        result["sysname"] = parts[0]
    if len(parts) > 2:
        result["release"] = parts[2]
    return result


def parse_cpuinfo(text: str) -> dict[str, Any]:
    """Parse `/proc/cpuinfo` output."""

    processors = sorted({int(match) for match in CPU_ID_RE.findall(text)})
    features: set[str] = set()
    implementers: set[str] = set()
    parts: set[str] = set()
    hardware = ""

    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        lower_key = key.lower()
        if lower_key == "features":
            features.update(value.split())
        elif lower_key == "hardware":
            hardware = value
        elif lower_key == "cpu implementer":
            implementers.add(value)
        elif lower_key == "cpu part":
            parts.add(value)

    result: dict[str, Any] = {
        "processor_count": len(processors),
        "features": sorted(features),
    }
    if processors:
        result["processors"] = processors
    if hardware:
        result["hardware"] = hardware
    if implementers:
        result["implementers"] = sorted(implementers)
    if parts:
        result["parts"] = sorted(parts)
    if not processors and not text.strip():
        result["warnings"] = ["raw_cpuinfo.txt was empty"]
    return result


def parse_meminfo(text: str) -> dict[str, Any]:
    """Parse `/proc/meminfo` output."""

    values: dict[str, int] = {}
    for key, value in MEMINFO_RE.findall(text):
        values[key] = int(value)

    result: dict[str, Any] = {"values_kb": values}
    if "MemTotal" in values:
        result["mem_total_kb"] = values["MemTotal"]
    if "MemAvailable" in values:
        result["mem_available_kb"] = values["MemAvailable"]
    if "SwapTotal" in values:
        result["swap_total_kb"] = values["SwapTotal"]
    if not values:
        result["warnings"] = ["no meminfo values parsed"]
    return result


def parse_thermal(text: str) -> dict[str, Any]:
    """Parse a marked dump of Android thermal sysfs files."""

    sections = _parse_marked_sections(text)
    zones: dict[int, dict[str, Any]] = {}
    devices: dict[int, dict[str, Any]] = {}
    warnings = _warnings_from_text(text)

    for path, value in sections.items():
        clean = _first_data_line(value)
        zone_match = re.search(r"/thermal_zone(\d+)/(type|temp)$", path)
        if zone_match:
            zone_index = int(zone_match.group(1))
            zone = zones.setdefault(zone_index, {"index": zone_index})
            key = zone_match.group(2)
            parsed = _parse_int(clean)
            zone[key] = parsed if parsed is not None and key == "temp" else clean
            continue

        cooling_match = re.search(r"/cooling_device(\d+)/(type|cur_state|max_state)$", path)
        if cooling_match:
            device_index = int(cooling_match.group(1))
            device = devices.setdefault(device_index, {"index": device_index})
            key = cooling_match.group(2)
            parsed = _parse_int(clean)
            device[key] = parsed if parsed is not None and key != "type" else clean

    result: dict[str, Any] = {
        "thermal_zones": [zones[index] for index in sorted(zones)],
        "cooling_devices": [devices[index] for index in sorted(devices)],
    }
    if warnings:
        result["warnings"] = warnings
    if not zones and not devices and text.strip():
        result.setdefault("warnings", []).append("no thermal sysfs values parsed")
    return result


def parse_sysfs_cpu(text: str) -> dict[str, Any]:
    """Parse a marked dump of Android CPU sysfs files."""

    sections = _parse_marked_sections(text)
    per_core_freqs: dict[str, dict[str, Any]] = {}
    governors: dict[str, str] = {}
    topology: dict[str, dict[str, Any]] = {}
    result: dict[str, Any] = {}
    warnings = _warnings_from_text(text)

    exact_fields = {
        "/sys/devices/system/cpu/possible": "possible",
        "/sys/devices/system/cpu/present": "present",
        "/sys/devices/system/cpu/online": "online",
    }
    freq_fields = {
        "cpuinfo_max_freq": "cpuinfo_max_freq_khz",
        "cpuinfo_min_freq": "cpuinfo_min_freq_khz",
        "scaling_cur_freq": "scaling_cur_freq_khz",
    }

    for path, value in sections.items():
        clean = _first_data_line(value)
        if path in exact_fields:
            result[exact_fields[path]] = clean
            continue

        match = re.search(r"/cpu(\d+)/(?:cpufreq|topology)/([^/]+)$", path)
        if not match:
            continue
        cpu = f"cpu{int(match.group(1))}"
        leaf = match.group(2)
        parsed = _parse_int(clean)

        if leaf in freq_fields:
            per_core_freqs.setdefault(cpu, {})[freq_fields[leaf]] = parsed if parsed is not None else clean
        elif leaf == "scaling_governor":
            governors[cpu] = clean
        elif leaf in {"physical_package_id", "core_id", "cluster_id", "cpu_capacity"}:
            topology.setdefault(cpu, {})[leaf] = parsed if parsed is not None else clean

    if per_core_freqs:
        result["per_core_freqs"] = _sort_cpu_dict(per_core_freqs)
    if governors:
        result["governors"] = _sort_cpu_dict(governors)
    if topology:
        result["topology"] = _sort_cpu_dict(topology)
    clusters = _cluster_heuristic(per_core_freqs, topology)
    if clusters:
        result["clusters"] = clusters
    if warnings:
        result["warnings"] = warnings
    return result


def parse_gpu_probe(text: str) -> dict[str, Any]:
    """Parse best-effort GPU/Vulkan/OpenCL/GLES hints."""

    vulkan_hints = _matching_lines(text, ["vulkan", "libvulkan"])
    opencl_hints = _matching_lines(text, ["opencl", "libOpenCL"])
    gles_hints = _matching_lines(text, ["gles", "libGLES", "egl"])
    adreno_hints = _matching_lines(text, ["adreno", "kgsl"])
    result: dict[str, Any] = {
        "vulkan_libraries_detected": bool(vulkan_hints),
        "opencl_libraries_detected": bool(opencl_hints),
        "gles_libraries_detected": bool(gles_hints),
        "vulkan_hints": vulkan_hints,
        "opencl_hints": opencl_hints,
        "gles_hints": gles_hints,
        "adreno_hints": adreno_hints,
    }
    warnings = _warnings_from_text(text)
    if warnings:
        result["warnings"] = warnings
    return result


def parse_npu_probe(text: str) -> dict[str, Any]:
    """Parse best-effort NPU, QNN, NNAPI, Hexagon DSP, and HTP hints."""

    qnn_libraries = sorted({match.group(0) for match in QNN_LIB_RE.finditer(text)})
    nnapi_hints = _matching_lines(text, ["nnapi", "neuralnetworks", "neural"])
    hexagon_dsp_hints = _matching_lines(text, ["hexagon", "dsp", "cdsprpc", "libhexagon_nn"])
    htp_hints = _matching_lines(text, ["htp", "hta"])
    any_hints = bool(qnn_libraries or nnapi_hints or hexagon_dsp_hints or htp_hints)
    status = "unknown" if not text.strip() else "hints_detected" if any_hints else "not_detected"

    result: dict[str, Any] = {
        "qnn_libraries_detected": bool(qnn_libraries),
        "qnn_libraries": qnn_libraries,
        "nnapi_hints": nnapi_hints,
        "hexagon_dsp_hints": hexagon_dsp_hints,
        "htp_hints": htp_hints,
        "status": status,
    }
    warnings = _warnings_from_text(text)
    if warnings:
        result["warnings"] = warnings
    return result


def build_probe_result(raw_dir: Path) -> dict[str, Any]:
    """Build a schema-valid probe result from a directory of raw ADB files."""

    raw_dir = Path(raw_dir)
    raw_texts: dict[str, str] = {}
    warnings: list[str] = []
    for key, filename in RAW_FILES.items():
        path = raw_dir / filename
        if not path.exists():
            warnings.append(f"missing raw file: {filename}")
            raw_texts[key] = ""
            continue
        raw_texts[key] = path.read_text(encoding="utf-8", errors="replace")

    device = parse_getprop(raw_texts["getprop"])
    uname = parse_uname(raw_texts["uname"])
    if "kernel" in uname:
        device["kernel"] = uname["kernel"]
    if "release" in uname:
        device["kernel_release"] = uname["release"]

    cpu = parse_cpuinfo(raw_texts["cpuinfo"])
    sysfs_cpu = parse_sysfs_cpu(raw_texts["sysfs_cpu"])
    if sysfs_cpu:
        cpu["sysfs"] = sysfs_cpu
    if cpu.get("processor_count", 0) == 0:
        inferred_count = _count_cpu_list(sysfs_cpu.get("online") or sysfs_cpu.get("present") or "")
        if inferred_count:
            cpu["processor_count"] = inferred_count
            cpu["processor_count_source"] = "sysfs"

    memory = parse_meminfo(raw_texts["meminfo"])
    thermal = parse_thermal(raw_texts["thermal"])
    gpu = parse_gpu_probe(raw_texts["gpu"])
    npu = parse_npu_probe(raw_texts["npu"])

    warnings.extend(_prefixed_warnings("uname", uname))
    warnings.extend(_prefixed_warnings("cpu", cpu))
    warnings.extend(_prefixed_warnings("memory", memory))
    warnings.extend(_prefixed_warnings("thermal", thermal))
    warnings.extend(_prefixed_warnings("gpu", gpu))
    warnings.extend(_prefixed_warnings("npu", npu))
    if device.get("property_count", 0) == 0:
        warnings.append("getprop: no Android properties parsed")

    return {
        "schema_version": "0.1",
        "timestamp_utc": utc_now_iso(),
        "source": "adb-host-probe",
        "device": device,
        "cpu": cpu,
        "memory": memory,
        "gpu": gpu,
        "npu": npu,
        "thermal": thermal,
        "microbenchmarks": {
            "phase1_note": "host-side adb probe only; no native microbenchmarks run",
        },
        "warnings": _unique(warnings),
    }


def write_probe_result(raw_dir: Path, out_json: Path) -> None:
    """Build, validate, and write a probe result JSON file."""

    probe = build_probe_result(Path(raw_dir))
    errors = validate_probe_result(probe)
    if errors:
        raise ValueError("probe result validation failed: " + "; ".join(errors))
    out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(probe, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def recommended_backend_order(probe: dict[str, Any]) -> list[str]:
    """Return a conservative backend order from a parsed probe result."""

    backends: list[str] = []
    npu = probe.get("npu", {})
    gpu = probe.get("gpu", {})
    if isinstance(npu, dict) and npu.get("qnn_libraries_detected") is True:
        backends.append("qnn")
    if isinstance(npu, dict) and npu.get("nnapi_hints"):
        backends.append("nnapi")
    if isinstance(gpu, dict) and gpu.get("vulkan_libraries_detected") is True:
        backends.append("vulkan")
    backends.append("cpu")
    return backends


def _first(properties: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        value = properties.get(key, "").strip()
        if value:
            return value
    return ""


def _set_if_present(target: dict[str, Any], key: str, value: Any) -> None:
    if value not in ("", None, []):
        target[key] = value


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    stripped = str(value).strip()
    if not re.fullmatch(r"-?\d+", stripped):
        return None
    return int(stripped)


def _strip_command_echo(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("$ ")]
    return lines[0] if lines else ""


def _parse_marked_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    buffer: list[str] = []
    for line in text.splitlines():
        if line.startswith("### "):
            if current is not None:
                sections[current] = "\n".join(buffer).strip()
            current = line[4:].strip()
            buffer = []
        elif current is not None:
            buffer.append(line)
    if current is not None:
        sections[current] = "\n".join(buffer).strip()
    return sections


def _first_data_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _warnings_from_text(text: str) -> list[str]:
    warnings: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if not stripped:
            continue
        if (
            "permission denied" in lowered
            or "no such file" in lowered
            or "not found" in lowered
            or "inaccessible" in lowered
            or lowered.startswith("error:")
            or "failed" in lowered
        ):
            warnings.append(stripped)
    return _unique(warnings)


def _matching_lines(text: str, needles: list[str]) -> list[str]:
    lowered_needles = [needle.lower() for needle in needles]
    matches: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if stripped and any(needle in lowered for needle in lowered_needles):
            matches.append(stripped)
    return _unique(matches)


def _sort_cpu_dict(data: dict[str, Any]) -> dict[str, Any]:
    return {key: data[key] for key in sorted(data, key=_cpu_sort_key)}


def _cpu_sort_key(cpu: str) -> int:
    match = re.search(r"(\d+)$", cpu)
    return int(match.group(1)) if match else 0


def _cluster_heuristic(
    per_core_freqs: dict[str, dict[str, Any]],
    topology: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, Any], list[str]] = {}
    for cpu in set(per_core_freqs) | set(topology):
        max_freq = per_core_freqs.get(cpu, {}).get("cpuinfo_max_freq_khz")
        capacity = topology.get(cpu, {}).get("cpu_capacity")
        if max_freq is None and capacity is None:
            continue
        groups.setdefault((max_freq, capacity), []).append(cpu)

    clusters: list[dict[str, Any]] = []
    for index, ((max_freq, capacity), cores) in enumerate(sorted(groups.items(), key=lambda item: str(item[0]))):
        cluster: dict[str, Any] = {"cluster_id": index, "cores": sorted(cores, key=_cpu_sort_key)}
        if max_freq is not None:
            cluster["cpuinfo_max_freq_khz"] = max_freq
        if capacity is not None:
            cluster["cpu_capacity"] = capacity
        clusters.append(cluster)
    return clusters


def _count_cpu_list(value: str) -> int:
    total = 0
    for part in value.split(","):
        item = part.strip()
        if not item:
            continue
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start = _parse_int(start_text)
            end = _parse_int(end_text)
            if start is not None and end is not None and end >= start:
                total += end - start + 1
        elif _parse_int(item) is not None:
            total += 1
    return total


def _prefixed_warnings(prefix: str, parsed: dict[str, Any]) -> list[str]:
    warnings = parsed.get("warnings", [])
    if not isinstance(warnings, list):
        return []
    return [f"{prefix}: {warning}" for warning in warnings]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value not in seen:
            unique_values.append(value)
            seen.add(value)
    return unique_values

