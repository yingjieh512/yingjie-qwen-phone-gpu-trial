"""Execution-model-neutral hardware characterization from Android probes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from qpnpu.android_probe import read_android_probe, summarize_android_probe


REQUIRED_HARDWARE_MODEL_KEYS = [
    "schema_version",
    "source",
    "target",
    "execution_units",
    "memory",
    "runtime_access",
    "probe_gaps",
    "fuzzing_plan",
    "next_gates",
    "warnings",
]


def validate_hardware_model(data: dict[str, Any]) -> list[str]:
    """Validate the Phase 4 hardware characterization model."""

    if not isinstance(data, dict):
        return ["hardware model must be a JSON object"]
    errors: list[str] = []
    for key in REQUIRED_HARDWARE_MODEL_KEYS:
        if key not in data:
            errors.append(f"missing required key: {key}")
    for key in ["source", "target", "memory"]:
        if key in data and not isinstance(data[key], dict):
            errors.append(f"{key} must be an object")
    for key in ["execution_units", "runtime_access", "probe_gaps", "fuzzing_plan", "next_gates", "warnings"]:
        if key in data and not isinstance(data[key], list):
            errors.append(f"{key} must be a list")
    return errors


def characterize_android_probe(probe: dict[str, Any]) -> dict[str, Any]:
    """Build an execution-model-neutral hardware model from Android probe JSON."""

    summary = summarize_android_probe(probe)
    device = _object(summary.get("device"))
    cpu = _object(summary.get("cpu"))
    memory = _object(summary.get("memory"))
    gpu = _object(summary.get("gpu"))
    npu = _object(summary.get("npu"))
    thermal = _object(summary.get("thermal"))
    source = _object(summary.get("source_probe"))

    execution_units = [
        _cpu_unit(device, cpu),
        _gpu_unit(gpu),
        _npu_hint_unit(npu),
    ]
    if thermal.get("zone_count", 0):
        execution_units.append(_thermal_unit(thermal))

    model = {
        "schema_version": "0.1",
        "source": {
            "probe_source": source.get("source", ""),
            "probe_timestamp_utc": source.get("timestamp_utc", ""),
            "artifact_kind": "android_probe_json",
        },
        "target": {
            "phone": "Samsung Galaxy S26 Ultra",
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
        "execution_model_neutral": True,
        "execution_units": execution_units,
        "memory": {
            "host_device_memory_model": "unified_android_process_memory_observed",
            "mem_total_kb": memory.get("mem_total_kb"),
            "mem_available_kb": memory.get("mem_available_kb"),
            "runtime_max_memory_bytes": memory.get("runtime_max_memory_bytes"),
            "evidence": ["app Runtime memory", "/proc/meminfo"],
        },
        "runtime_access": [
            {
                "id": "android_app_java",
                "status": "working",
                "evidence": "probe APK installed, launched, read files, ran shell getprop, and emitted logcat JSON",
            },
            {
                "id": "android_native_jni",
                "status": "planned",
                "evidence": "needed for safe instruction and kernel probes",
            },
            {
                "id": "qnn_runtime",
                "status": "unknown",
                "evidence": "no direct libQnn*.so evidence in first probe",
            },
            {
                "id": "vulkan_runtime",
                "status": "unknown",
                "evidence": "GPU/OpenCL/GLES hints found; Vulkan not proven in first probe",
            },
        ],
        "probe_gaps": _probe_gaps(gpu, npu),
        "fuzzing_plan": _fuzzing_plan(),
        "next_gates": [
            "android_native_smoke_jni",
            "cpu_isa_feature_probe",
            "native_kernel_correctness_microfixtures",
            "native_cpu_microbench_json",
            "backend_runtime_load_probe",
        ],
        "warnings": [
            "hardware characterization is based on Android app-accessible evidence only",
            "string hints do not prove accelerator execution",
            "no Qwen 9B inference was run",
            "no performance target was measured",
        ],
    }
    return model


def read_and_characterize_android_probe(path: str | Path) -> dict[str, Any]:
    """Read Android probe JSON and return the neutral hardware model."""

    return characterize_android_probe(read_android_probe(path))


def render_hardware_model_markdown(model: dict[str, Any]) -> str:
    """Render a hardware model as a concise markdown report."""

    errors = validate_hardware_model(model)
    if errors:
        raise ValueError("invalid hardware model: " + "; ".join(errors))

    target = _object(model.get("target"))
    units = _list(model.get("execution_units"))
    gaps = _strings(model.get("probe_gaps"))
    gates = _strings(model.get("next_gates"))

    lines = [
        "# Execution-Model-Neutral Hardware Characterization",
        "",
        "This document is a conservative hardware model generated from Android probe evidence. It is not a performance report.",
        "",
        "## Target",
        "",
        f"- Phone: {target.get('phone', '')}",
        f"- Model: {target.get('manufacturer', '')} {target.get('model', '')}",
        f"- SoC: {target.get('soc_manufacturer', '')} {target.get('soc_model', '')}",
        f"- Android: {target.get('android_release', '')} / SDK {target.get('sdk_version', '')}",
        f"- ABIs: {', '.join(_strings(target.get('supported_abis')))}",
        "",
        "## Execution Units",
        "",
    ]
    for unit in units:
        unit_obj = _object(unit)
        lines.extend(
            [
                f"### {unit_obj.get('id', '')}",
                "",
                f"- Kind: {unit_obj.get('kind', '')}",
                f"- Status: {unit_obj.get('status', '')}",
                f"- Access: {unit_obj.get('access', '')}",
                f"- Confidence: {unit_obj.get('confidence', '')}",
                f"- Execution model: {_object(unit_obj.get('execution_model')).get('model', '')}",
                f"- Evidence: {'; '.join(_strings(unit_obj.get('evidence')))}",
                "",
            ]
        )

    lines.extend(
        [
            "## Probe Gaps",
            "",
            *[f"- {gap}" for gap in gaps],
            "",
            "## Next Gates",
            "",
            *[f"- {gate}" for gate in gates],
            "",
            "## Structured Fuzzing Plan",
            "",
        ]
    )
    for item in _list(model.get("fuzzing_plan")):
        plan = _object(item)
        lines.extend(
            [
                f"### {plan.get('id', '')}",
                "",
                f"- Purpose: {plan.get('purpose', '')}",
                f"- Requires: {plan.get('requires', '')}",
                f"- Safety: {plan.get('safety', '')}",
                f"- Output: {', '.join(_strings(plan.get('outputs')))}",
                "",
            ]
        )
    return "\n".join(lines)


def write_hardware_model_json(path: str | Path, model: dict[str, Any]) -> Path:
    """Write the hardware characterization JSON artifact."""

    errors = validate_hardware_model(model)
    if errors:
        raise ValueError("invalid hardware model: " + "; ".join(errors))
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def write_hardware_model_markdown(path: str | Path, model: dict[str, Any]) -> Path:
    """Write the hardware characterization markdown artifact."""

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_hardware_model_markdown(model) + "\n", encoding="utf-8")
    return out


def _cpu_unit(device: dict[str, Any], cpu: dict[str, Any]) -> dict[str, Any]:
    feature_summary = _object(cpu.get("feature_summary"))
    return {
        "id": "cpu.arm64.app_process",
        "kind": "cpu",
        "status": "reachable",
        "access": "android_app_process",
        "confidence": "high",
        "execution_model": {
            "model": "shared_memory_os_threads",
            "simd_model": "arm64_feature_flags_from_proc_cpuinfo",
            "host_device_memory": "unified",
        },
        "features": {
            "available_processors": cpu.get("available_processors"),
            "present_cpu_flags": _strings(feature_summary.get("present")),
            "missing_cpu_flags": _strings(feature_summary.get("missing")),
            "soc_model": device.get("soc_model", ""),
        },
        "evidence": ["/proc/cpuinfo readable", "Runtime.availableProcessors"],
    }


def _gpu_unit(gpu: dict[str, Any]) -> dict[str, Any]:
    hints = _strings(gpu.get("notable_hints"))
    return {
        "id": "gpu.adreno.hints",
        "kind": "gpu",
        "status": str(gpu.get("status", "unknown")),
        "access": "library_listing_only",
        "confidence": "medium" if hints else "low",
        "execution_model": {
            "model": "unknown_gpu_runtime",
            "simd_model": "unknown",
            "host_device_memory": "shared_or_driver_managed_unknown",
        },
        "features": {
            "vulkan_libraries_detected": bool(gpu.get("vulkan_libraries_detected")),
            "hint_count": gpu.get("hint_count"),
            "notable_hints": hints,
        },
        "evidence": ["Android library listings", "getprop ro.hardware.egl when available"],
    }


def _npu_hint_unit(npu: dict[str, Any]) -> dict[str, Any]:
    hints = _strings(npu.get("notable_hints"))
    return {
        "id": "accelerator.cdsp_htp_qnn.hints",
        "kind": "npu_or_dsp_hint",
        "status": str(npu.get("status", "unknown")),
        "access": "library_listing_only",
        "confidence": "medium" if hints else "low",
        "execution_model": {
            "model": "unknown_dsp_or_npu_runtime",
            "simd_model": "unknown",
            "host_device_memory": "driver_managed_unknown",
        },
        "features": {
            "qnn_libraries_detected": bool(npu.get("qnn_libraries_detected")),
            "nnapi_string_hints_detected": bool(npu.get("nnapi_string_hints_detected")),
            "hint_count": npu.get("hint_count"),
            "notable_hints": hints,
        },
        "evidence": ["Android library listings", "thermal/cooling CDSP hints if present"],
    }


def _thermal_unit(thermal: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "thermal.cooling_control",
        "kind": "thermal",
        "status": str(thermal.get("status", "unknown")),
        "access": "sysfs_read_only",
        "confidence": "high",
        "execution_model": {
            "model": "telemetry_and_throttling_context",
            "simd_model": "not_applicable",
            "host_device_memory": "not_applicable",
        },
        "features": {
            "zone_count": thermal.get("zone_count"),
            "notable_zones": _strings(thermal.get("notable_zones")),
        },
        "evidence": ["/sys/class/thermal readable"],
    }


def _probe_gaps(gpu: dict[str, Any], npu: dict[str, Any]) -> list[str]:
    gaps = [
        "No JNI/NDK instruction probes have run yet.",
        "No native kernel correctness tests have run on Android yet.",
    ]
    if not gpu.get("vulkan_libraries_detected"):
        gaps.append("Vulkan availability requires real API enumeration; library hints were insufficient.")
    if not npu.get("qnn_libraries_detected"):
        gaps.append("QNN availability requires direct library load/API probing; first probe did not prove libQnn availability.")
    gaps.append("No accelerator execution or performance benchmark has run.")
    return gaps


def _fuzzing_plan() -> list[dict[str, Any]]:
    return [
        {
            "id": "cpu_arm64_isa_feature_probe",
            "purpose": "Validate reported CPU feature flags with tiny guarded native instructions.",
            "requires": "Android NDK/JNI",
            "safety": "Run one candidate per guarded probe using SIGILL handling or process isolation.",
            "outputs": ["feature_name", "compiled", "executed", "sigill_or_ok", "latency_ns_optional"],
        },
        {
            "id": "thread_topology_probe",
            "purpose": "Map CPU thread scaling and infer big/mid/little behavior from latency and affinity when allowed.",
            "requires": "Android NDK/JNI",
            "safety": "Use short bounded loops and record thermal state.",
            "outputs": ["threads", "latency", "throughput", "thermal_snapshot"],
        },
        {
            "id": "memory_hierarchy_probe",
            "purpose": "Measure app-visible memory bandwidth and latency regimes for kernel tiling decisions.",
            "requires": "Android NDK/JNI",
            "safety": "Use small buffers first; cap allocation sizes well below available memory.",
            "outputs": ["buffer_bytes", "stride", "bandwidth_gbps", "latency_ns"],
        },
        {
            "id": "backend_runtime_load_probe",
            "purpose": "Check whether Vulkan, NNAPI, QNN, or SNPE-like libraries can be loaded and minimally enumerated.",
            "requires": "Android Java APIs plus optional NDK dlopen",
            "safety": "Load and unload libraries only; do not execute untrusted accelerator kernels.",
            "outputs": ["backend", "library", "load_status", "api_version_or_error"],
        },
        {
            "id": "native_kernel_correctness_probe",
            "purpose": "Run tiny deterministic matvec, int4 dequant, RMSNorm, RoPE, and softmax kernels against references.",
            "requires": "Android NDK/JNI",
            "safety": "Tiny tensors only; no model weights.",
            "outputs": ["operator", "shape", "max_abs_error", "passed"],
        },
    ]


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]
