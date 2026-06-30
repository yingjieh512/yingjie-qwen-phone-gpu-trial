"""Validation helpers for future Android hardware probe results."""

from __future__ import annotations

from typing import Any

from qpnpu.config import utc_now_iso


REQUIRED_PROBE_KEYS = [
    "schema_version",
    "timestamp_utc",
    "source",
    "device",
    "cpu",
    "memory",
    "gpu",
    "npu",
    "thermal",
    "microbenchmarks",
    "warnings",
]


def minimal_probe_result() -> dict[str, Any]:
    """Return a valid, empty Phase 0 probe result."""

    return {
        "schema_version": "0.1",
        "timestamp_utc": utc_now_iso(),
        "source": "sample",
        "device": {},
        "cpu": {},
        "memory": {},
        "gpu": {},
        "npu": {},
        "thermal": {},
        "microbenchmarks": {},
        "warnings": [],
    }


def validate_probe_result(data: dict[str, Any]) -> list[str]:
    """Validate a probe result and return human-readable errors."""

    if not isinstance(data, dict):
        return ["probe result must be a JSON object"]

    errors: list[str] = []
    for key in REQUIRED_PROBE_KEYS:
        if key not in data:
            errors.append(f"missing required key: {key}")

    for key in ["device", "cpu", "memory", "gpu", "npu", "thermal", "microbenchmarks"]:
        if key in data and not isinstance(data[key], dict):
            errors.append(f"{key} must be an object")

    if "schema_version" in data and not isinstance(data["schema_version"], str):
        errors.append("schema_version must be a string")
    if "timestamp_utc" in data and not isinstance(data["timestamp_utc"], str):
        errors.append("timestamp_utc must be a string")
    if "source" in data and not isinstance(data["source"], str):
        errors.append("source must be a string")
    if "warnings" in data and not isinstance(data["warnings"], list):
        errors.append("warnings must be a list")

    return errors

