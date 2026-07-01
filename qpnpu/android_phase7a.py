"""Validation helpers for Android Phase 7A guarded ISA probe payloads."""

from __future__ import annotations

from typing import Any


REQUIRED_PHASE7A_KEYS = [
    "schema_version",
    "source",
    "backend",
    "native_library",
    "safety",
    "cpu_evidence",
    "isa_probes",
    "summary",
    "warnings",
]

VALID_PROBE_STATUSES = {
    "executed_ok",
    "sigill",
    "skipped_not_reported",
    "deferred_no_safe_probe",
    "not_compiled",
    "guard_install_failed",
    "unsupported_host_arch",
}


def validate_phase7a_isa_probes(data: dict[str, Any]) -> list[str]:
    """Validate a Phase 7A Android guarded ISA probe JSON object."""

    if not isinstance(data, dict):
        return ["phase7a ISA probes must be a JSON object"]

    errors: list[str] = []
    for key in REQUIRED_PHASE7A_KEYS:
        if key not in data:
            errors.append(f"missing required key: {key}")

    if data.get("source") != "android-phase7a-isa-probes":
        errors.append("source must be android-phase7a-isa-probes")
    if data.get("backend") != "cpu_android_native_reference":
        errors.append("backend must be cpu_android_native_reference")

    for key in ["safety", "cpu_evidence", "summary"]:
        if key in data and not isinstance(data[key], dict):
            errors.append(f"{key} must be an object")

    if "warnings" in data and not isinstance(data["warnings"], list):
        errors.append("warnings must be a list")

    safety = data.get("safety")
    if isinstance(safety, dict):
        if safety.get("strategy") != "sigaction_sigsetjmp_same_process":
            errors.append("safety.strategy must be sigaction_sigsetjmp_same_process")
        if safety.get("destructive_unreported_feature_trials") is not False:
            errors.append("destructive_unreported_feature_trials must be false")

    probes = data.get("isa_probes")
    if not isinstance(probes, list):
        errors.append("isa_probes must be a list")
        probes = []
    elif not probes:
        errors.append("isa_probes must not be empty")
    else:
        for index, probe in enumerate(probes):
            if not isinstance(probe, dict):
                errors.append(f"isa_probes[{index}] must be an object")
                continue
            for key in [
                "feature_name",
                "cpuinfo_token",
                "reported",
                "probe_id",
                "compiled",
                "guarded",
                "executed",
                "sigill",
                "status",
                "checksum",
            ]:
                if key not in probe:
                    errors.append(f"isa_probes[{index}] missing key: {key}")
            status = probe.get("status")
            if status not in VALID_PROBE_STATUSES:
                errors.append(f"isa_probes[{index}] invalid status: {status}")
            if probe.get("executed") is True and probe.get("compiled") is not True:
                errors.append(f"isa_probes[{index}] executed but compiled is not true")
            if probe.get("sigill") is True and probe.get("status") != "sigill":
                errors.append(f"isa_probes[{index}] sigill true but status is not sigill")
            if probe.get("status") == "executed_ok" and probe.get("executed") is not True:
                errors.append(f"isa_probes[{index}] executed_ok but executed is not true")

    summary = data.get("summary")
    if isinstance(summary, dict):
        for key in ["probe_count", "executed_ok_count", "sigill_count", "skipped_count"]:
            if key not in summary:
                errors.append(f"summary missing key: {key}")
            elif not isinstance(summary[key], int):
                errors.append(f"summary.{key} must be an integer")
        if isinstance(probes, list) and isinstance(summary.get("probe_count"), int):
            if summary["probe_count"] != len(probes):
                errors.append("summary.probe_count must match len(isa_probes)")
        count_keys = ["executed_ok_count", "sigill_count", "skipped_count"]
        if all(isinstance(summary.get(key), int) for key in count_keys) and isinstance(summary.get("probe_count"), int):
            if sum(summary[key] for key in count_keys) > summary["probe_count"]:
                errors.append("summary status counts cannot exceed probe_count")

    return errors