"""Kernel configuration validation and deterministic hashing."""

from __future__ import annotations

import hashlib
import json
from typing import Any


REQUIRED_KERNEL_CONFIG_KEYS = [
    "schema_version",
    "operator",
    "group_size",
    "tile_n",
    "unroll",
    "prefetch_distance",
    "accumulation_dtype",
]


def validate_kernel_config(data: dict[str, Any]) -> list[str]:
    """Validate a Phase 0 kernel config."""

    if not isinstance(data, dict):
        return ["kernel config must be a JSON object"]

    errors: list[str] = []
    for key in REQUIRED_KERNEL_CONFIG_KEYS:
        if key not in data:
            errors.append(f"missing required key: {key}")

    for key in ["schema_version", "operator", "accumulation_dtype"]:
        if key in data and not isinstance(data[key], str):
            errors.append(f"{key} must be a string")

    for key in ["group_size", "tile_n", "unroll"]:
        if key in data and (not isinstance(data[key], int) or data[key] <= 0):
            errors.append(f"{key} must be a positive integer")

    if "prefetch_distance" in data and (
        not isinstance(data["prefetch_distance"], int) or data["prefetch_distance"] < 0
    ):
        errors.append("prefetch_distance must be a non-negative integer")

    return errors


def kernel_config_hash(data: dict[str, Any]) -> str:
    """Return a deterministic 12-character SHA256 hash for a config."""

    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]

