"""Validation helpers for Android Phase 6 characterization payloads."""

from __future__ import annotations

from typing import Any


REQUIRED_PHASE6_KEYS = [
    "schema_version",
    "source",
    "backend",
    "native_library",
    "cpu_isa",
    "topology",
    "memory",
    "backend_load",
    "quantization",
    "warnings",
]


def validate_phase6_characterization(data: dict[str, Any]) -> list[str]:
    """Validate a Phase 6 Android characterization JSON object."""

    if not isinstance(data, dict):
        return ["phase6 characterization must be a JSON object"]

    errors: list[str] = []
    for key in REQUIRED_PHASE6_KEYS:
        if key not in data:
            errors.append(f"missing required key: {key}")

    if data.get("source") != "android-phase6-characterization":
        errors.append("source must be android-phase6-characterization")
    if data.get("backend") != "cpu_android_native_reference":
        errors.append("backend must be cpu_android_native_reference")

    for key in ["cpu_isa", "topology", "memory", "backend_load", "quantization"]:
        if key in data and not isinstance(data[key], dict):
            errors.append(f"{key} must be an object")

    if "warnings" in data and not isinstance(data["warnings"], list):
        errors.append("warnings must be a list")

    cpu_isa = data.get("cpu_isa")
    if isinstance(cpu_isa, dict):
        if not isinstance(cpu_isa.get("features", []), list):
            errors.append("cpu_isa.features must be a list")
        if not isinstance(cpu_isa.get("execution_probes", []), list):
            errors.append("cpu_isa.execution_probes must be a list")

    topology = data.get("topology")
    if isinstance(topology, dict) and not isinstance(topology.get("thread_scaling", []), list):
        errors.append("topology.thread_scaling must be a list")

    memory = data.get("memory")
    if isinstance(memory, dict) and not isinstance(memory.get("copy_bandwidth_cases", []), list):
        errors.append("memory.copy_bandwidth_cases must be a list")

    backend_load = data.get("backend_load")
    if isinstance(backend_load, dict):
        probes = backend_load.get("probes", [])
        if not isinstance(probes, list):
            errors.append("backend_load.probes must be a list")
        else:
            for index, probe in enumerate(probes):
                if not isinstance(probe, dict):
                    errors.append(f"backend_load.probes[{index}] must be an object")
                    continue
                for key in ["backend", "library", "status", "loaded"]:
                    if key not in probe:
                        errors.append(f"backend_load.probes[{index}] missing key: {key}")

    quantization = data.get("quantization")
    if isinstance(quantization, dict):
        fixtures = quantization.get("fixtures", [])
        if not isinstance(fixtures, list):
            errors.append("quantization.fixtures must be a list")
        else:
            for index, fixture in enumerate(fixtures):
                if not isinstance(fixture, dict):
                    errors.append(f"quantization.fixtures[{index}] must be an object")
                    continue
                if fixture.get("correctness_passed") is not True:
                    errors.append(f"quantization.fixtures[{index}] did not pass correctness")

    return errors
