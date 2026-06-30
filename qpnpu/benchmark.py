"""Benchmark schema helpers and simple result selection."""

from __future__ import annotations

import json
import math
from typing import Any

from qpnpu.config import utc_now_iso


REQUIRED_BENCHMARK_KEYS = [
    "schema_version",
    "timestamp_utc",
    "device",
    "model",
    "backend",
    "operator",
    "shape",
    "metrics",
    "thermal",
    "kernel_config_hash",
    "warnings",
]

REQUIRED_METRICS = [
    "latency_ms_p50",
    "latency_ms_p90",
    "latency_ms_p99",
    "tokens_per_second",
    "memory_rss_mb",
]


def minimal_benchmark_result() -> dict[str, Any]:
    """Return a valid, empty Phase 0 benchmark result."""

    return {
        "schema_version": "0.1",
        "timestamp_utc": utc_now_iso(),
        "device": {},
        "model": {},
        "backend": "cpu",
        "operator": "int4_matvec",
        "shape": {},
        "metrics": {
            "latency_ms_p50": 0.0,
            "latency_ms_p90": 0.0,
            "latency_ms_p99": 0.0,
            "tokens_per_second": 0.0,
            "memory_rss_mb": 0.0,
        },
        "thermal": {},
        "kernel_config_hash": "sample",
        "warnings": [],
    }


def validate_benchmark_result(data: dict[str, Any]) -> list[str]:
    """Validate a benchmark result and return human-readable errors."""

    if not isinstance(data, dict):
        return ["benchmark result must be a JSON object"]

    errors: list[str] = []
    for key in REQUIRED_BENCHMARK_KEYS:
        if key not in data:
            errors.append(f"missing required key: {key}")

    for key in ["device", "model", "shape", "metrics", "thermal"]:
        if key in data and not isinstance(data[key], dict):
            errors.append(f"{key} must be an object")

    if "warnings" in data and not isinstance(data["warnings"], list):
        errors.append("warnings must be a list")

    metrics = data.get("metrics")
    if isinstance(metrics, dict):
        for key in REQUIRED_METRICS:
            if key not in metrics:
                errors.append(f"missing required metric: {key}")
            elif not isinstance(metrics[key], (int, float)):
                errors.append(f"metric {key} must be numeric")

    for key in ["schema_version", "timestamp_utc", "backend", "operator", "kernel_config_hash"]:
        if key in data and not isinstance(data[key], str):
            errors.append(f"{key} must be a string")

    return errors


def benchmark_results_from_payload(data: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """Return benchmark result objects from either one JSON object or a list."""

    if isinstance(data, dict):
        return [data], validate_benchmark_result(data)

    if isinstance(data, list):
        results: list[dict[str, Any]] = []
        errors: list[str] = []
        for index, item in enumerate(data):
            if not isinstance(item, dict):
                errors.append(f"benchmark[{index}] must be a JSON object")
                continue
            item_errors = validate_benchmark_result(item)
            errors.extend(f"benchmark[{index}]: {error}" for error in item_errors)
            results.append(item)
        return results, errors

    return [], ["benchmark payload must be a JSON object or a list of objects"]


def select_best_benchmarks(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Choose the best result for each operator and shape group.

    Groups are keyed as ``operator|canonical_shape_json``. Positive tokens/sec
    wins. If neither candidate has positive tokens/sec, lower p50 latency wins.
    """

    best: dict[str, dict[str, Any]] = {}
    for result in results:
        if not isinstance(result, dict):
            continue
        operator = str(result.get("operator", "unknown"))
        shape = result.get("shape", {})
        try:
            shape_key = json.dumps(shape, sort_keys=True, separators=(",", ":"))
        except TypeError:
            shape_key = str(shape)
        group_key = f"{operator}|{shape_key}"

        current = best.get(group_key)
        if current is None or _is_better(result, current):
            best[group_key] = result
    return best


def _is_better(candidate: dict[str, Any], current: dict[str, Any]) -> bool:
    candidate_tps = _metric(candidate, "tokens_per_second", default=0.0)
    current_tps = _metric(current, "tokens_per_second", default=0.0)
    if candidate_tps > 0.0 or current_tps > 0.0:
        return candidate_tps > current_tps

    candidate_latency = _metric(candidate, "latency_ms_p50", default=math.inf)
    current_latency = _metric(current, "latency_ms_p50", default=math.inf)
    return candidate_latency < current_latency


def _metric(result: dict[str, Any], name: str, default: float) -> float:
    value = result.get("metrics", {}).get(name, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default