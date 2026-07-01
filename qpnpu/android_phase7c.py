"""Validation helpers for Android Phase 7C generated kernel candidate payloads."""

from __future__ import annotations

from typing import Any

from qpnpu.benchmark import validate_benchmark_result


REQUIRED_PHASE7C_KEYS = [
    "schema_version",
    "source",
    "backend",
    "native_library",
    "generator",
    "safety",
    "candidates",
    "summary",
    "warnings",
]

REQUIRED_CANDIDATE_KEYS = [
    "name",
    "operator",
    "target_feature",
    "candidate_type",
    "compiled",
    "reported",
    "executed",
    "sigill",
    "status",
    "shape",
    "correctness",
    "warnings",
    "notes",
]

VALID_STATUSES = {
    "passed_correctness",
    "failed_correctness",
    "sigill",
    "skipped_feature_not_reported",
    "not_compiled",
    "deferred_no_safe_kernel",
    "guard_install_failed",
}


def validate_phase7c_generated_kernels(data: dict[str, Any]) -> list[str]:
    """Validate a Phase 7C Android generated-kernel candidate payload."""

    if not isinstance(data, dict):
        return ["Phase 7C payload must be a JSON object"]

    errors: list[str] = []
    for key in REQUIRED_PHASE7C_KEYS:
        if key not in data:
            errors.append(f"missing required key: {key}")

    if data.get("source") != "android-phase7c-generated-kernels":
        errors.append("source must be android-phase7c-generated-kernels")
    if data.get("backend") != "cpu_android_generated_candidate":
        errors.append("backend must be cpu_android_generated_candidate")

    for key in ["generator", "safety", "summary"]:
        if key in data and not isinstance(data[key], dict):
            errors.append(f"{key} must be an object")
    if "warnings" in data and not isinstance(data["warnings"], list):
        errors.append("warnings must be a list")

    safety = data.get("safety")
    if isinstance(safety, dict):
        if safety.get("uses_sigill_guard") is not True:
            errors.append("safety.uses_sigill_guard must be true")
        if safety.get("destructive_unreported_feature_trials") is not False:
            errors.append("safety.destructive_unreported_feature_trials must be false")

    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        errors.append("candidates must be a list")
        candidates = []

    counters = {
        "candidate_count": len(candidates),
        "executed_count": 0,
        "passed_count": 0,
        "sigill_count": 0,
        "skipped_count": 0,
        "deferred_count": 0,
        "experimental_count": 0,
    }
    all_executed_correctness_passed = True

    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            errors.append(f"candidates[{index}] must be an object")
            continue
        errors.extend(_validate_candidate(candidate, index))

        if candidate.get("executed") is True:
            counters["executed_count"] += 1
        if candidate.get("correctness", {}).get("passed") is True:
            counters["passed_count"] += 1
        if candidate.get("sigill") is True:
            counters["sigill_count"] += 1
        if candidate.get("status") in {"skipped_feature_not_reported", "not_compiled"}:
            counters["skipped_count"] += 1
        if candidate.get("status") == "deferred_no_safe_kernel":
            counters["deferred_count"] += 1
        if "experimental" in str(candidate.get("candidate_type", "")):
            counters["experimental_count"] += 1
        if candidate.get("executed") is True and candidate.get("correctness", {}).get("passed") is not True:
            all_executed_correctness_passed = False

    summary = data.get("summary")
    if isinstance(summary, dict):
        for key, value in counters.items():
            if summary.get(key) != value:
                errors.append(f"summary.{key} must equal {value}")
        if summary.get("all_executed_correctness_passed") != all_executed_correctness_passed:
            errors.append(
                "summary.all_executed_correctness_passed must match executed candidate correctness"
            )

    warnings = data.get("warnings")
    if isinstance(warnings, list):
        joined = " ".join(str(item).lower() for item in warnings)
        for required in ["generated", "cpu", "not qwen 9b", "not qnn", "not a performance"]:
            if required not in joined:
                errors.append(f"warnings must mention {required}")

    return errors


def _validate_candidate(candidate: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    prefix = f"candidates[{index}]"
    for key in REQUIRED_CANDIDATE_KEYS:
        if key not in candidate:
            errors.append(f"{prefix}: missing required key: {key}")

    for key in ["name", "operator", "target_feature", "candidate_type", "status", "notes"]:
        if key in candidate and not isinstance(candidate[key], str):
            errors.append(f"{prefix}.{key} must be a string")
    for key in ["compiled", "reported", "executed", "sigill"]:
        if key in candidate and not isinstance(candidate[key], bool):
            errors.append(f"{prefix}.{key} must be a boolean")
    if candidate.get("status") not in VALID_STATUSES:
        errors.append(f"{prefix}.status is not recognized: {candidate.get('status')}")
    if "shape" in candidate and not isinstance(candidate["shape"], dict):
        errors.append(f"{prefix}.shape must be an object")
    if "warnings" in candidate and not isinstance(candidate["warnings"], list):
        errors.append(f"{prefix}.warnings must be a list")

    correctness = candidate.get("correctness")
    if not isinstance(correctness, dict):
        errors.append(f"{prefix}.correctness must be an object")
    else:
        if not isinstance(correctness.get("passed"), bool):
            errors.append(f"{prefix}.correctness.passed must be a boolean")
        if not isinstance(correctness.get("max_abs_error"), (int, float)):
            errors.append(f"{prefix}.correctness.max_abs_error must be numeric")
        if not isinstance(correctness.get("checksum"), int):
            errors.append(f"{prefix}.correctness.checksum must be an integer")

    if candidate.get("executed") is True and candidate.get("sigill") is not True:
        benchmark = candidate.get("benchmark")
        if not isinstance(benchmark, dict):
            errors.append(f"{prefix}.benchmark must exist for executed non-SIGILL candidates")
        else:
            errors.extend(f"{prefix}.benchmark: {error}" for error in validate_benchmark_result(benchmark))
            if benchmark.get("backend") != "cpu_android_generated_candidate":
                errors.append(f"{prefix}.benchmark.backend must be cpu_android_generated_candidate")
            if benchmark.get("operator") != candidate.get("operator"):
                errors.append(f"{prefix}.benchmark.operator must match candidate.operator")

    if candidate.get("status") == "passed_correctness" and candidate.get("correctness", {}).get("passed") is not True:
        errors.append(f"{prefix}.status passed_correctness requires correctness.passed true")
    if candidate.get("status") == "deferred_no_safe_kernel" and candidate.get("executed") is not False:
        errors.append(f"{prefix}.deferred_no_safe_kernel candidates must not execute")

    return errors