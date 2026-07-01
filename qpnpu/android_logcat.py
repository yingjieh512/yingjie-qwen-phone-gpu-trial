"""Extract QPNPU Android JSON payloads from logcat text."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from qpnpu.android_phase6 import validate_phase6_characterization
from qpnpu.benchmark import benchmark_results_from_payload
from qpnpu.probe_schema import validate_probe_result


LOGCAT_MESSAGE_RE = re.compile(r"^.*?\s[VDIWEF]\sQPNPUProbe:\s?(.*)$")
BEGIN_MARKER = "QPNPU_PROBE_JSON_BEGIN"
END_MARKER = "QPNPU_PROBE_JSON_END"
NATIVE_BENCH_BEGIN_MARKER = "QPNPU_NATIVE_BENCH_JSON_BEGIN"
NATIVE_BENCH_END_MARKER = "QPNPU_NATIVE_BENCH_JSON_END"
PHASE6_BEGIN_MARKER = "QPNPU_PHASE6_JSON_BEGIN"
PHASE6_END_MARKER = "QPNPU_PHASE6_JSON_END"


def extract_probe_json_from_logcat_text(text: str) -> dict[str, Any]:
    """Extract and validate probe JSON emitted between QPNPU logcat markers."""

    data = _extract_json_with_markers(text, BEGIN_MARKER, END_MARKER)
    validation_errors = validate_probe_result(data)
    if validation_errors:
        raise ValueError("invalid extracted probe JSON: " + "; ".join(validation_errors))
    return data


def extract_probe_json_from_logcat_file(path: str | Path) -> dict[str, Any]:
    """Read a logcat text file and extract the probe JSON object."""

    return extract_probe_json_from_logcat_text(Path(path).read_text(encoding="utf-8"))


def write_extracted_probe_json(logcat_path: str | Path, out_path: str | Path) -> Path:
    """Extract probe JSON from a logcat file and write pretty JSON."""

    data = extract_probe_json_from_logcat_file(logcat_path)
    return _write_json(data, out_path)


def extract_native_benchmark_json_from_logcat_text(text: str) -> dict[str, Any]:
    """Extract and validate native microbenchmark JSON from QPNPU logcat markers."""

    data = _extract_json_with_markers(text, NATIVE_BENCH_BEGIN_MARKER, NATIVE_BENCH_END_MARKER)
    validation_errors = _validate_native_benchmark_payload(data)
    if validation_errors:
        raise ValueError("invalid extracted native benchmark JSON: " + "; ".join(validation_errors))
    return data


def extract_native_benchmark_json_from_logcat_file(path: str | Path) -> dict[str, Any]:
    """Read a logcat text file and extract the native microbenchmark JSON object."""

    return extract_native_benchmark_json_from_logcat_text(Path(path).read_text(encoding="utf-8"))


def write_extracted_native_benchmark_json(logcat_path: str | Path, out_path: str | Path) -> Path:
    """Extract native microbenchmark JSON from logcat and write pretty JSON."""

    data = extract_native_benchmark_json_from_logcat_file(logcat_path)
    return _write_json(data, out_path)




def extract_phase6_characterization_json_from_logcat_text(text: str) -> dict[str, Any]:
    """Extract and validate Phase 6 characterization JSON from QPNPU logcat markers."""

    data = _extract_json_with_markers(text, PHASE6_BEGIN_MARKER, PHASE6_END_MARKER)
    validation_errors = validate_phase6_characterization(data)
    if validation_errors:
        raise ValueError("invalid extracted Phase 6 characterization JSON: " + "; ".join(validation_errors))
    return data


def extract_phase6_characterization_json_from_logcat_file(path: str | Path) -> dict[str, Any]:
    """Read a logcat text file and extract the Phase 6 characterization JSON object."""

    return extract_phase6_characterization_json_from_logcat_text(Path(path).read_text(encoding="utf-8"))


def write_extracted_phase6_characterization_json(logcat_path: str | Path, out_path: str | Path) -> Path:
    """Extract Phase 6 characterization JSON from logcat and write pretty JSON."""

    data = extract_phase6_characterization_json_from_logcat_file(logcat_path)
    return _write_json(data, out_path)

def _extract_json_with_markers(text: str, begin_marker: str, end_marker: str) -> dict[str, Any]:
    chunks: list[str] = []
    inside = False
    saw_begin = False
    saw_end = False

    for line in text.splitlines():
        match = LOGCAT_MESSAGE_RE.match(line)
        if not match:
            continue
        message = match.group(1)
        if begin_marker in message:
            inside = True
            saw_begin = True
            continue
        if end_marker in message:
            saw_end = True
            break
        if inside:
            chunks.append(message)

    if not saw_begin:
        raise ValueError(f"missing {begin_marker}")
    if not saw_end:
        raise ValueError(f"missing {end_marker}")
    if not chunks:
        raise ValueError("no QPNPU JSON chunks found")

    errors: list[str] = []
    for separator in ("", "\n"):
        candidate = separator.join(chunks)
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError as exc:
            errors.append(str(exc))
            continue
        if not isinstance(data, dict):
            raise ValueError("extracted QPNPU JSON must be an object")
        return data

    raise ValueError("failed to parse QPNPU JSON from logcat chunks: " + " | ".join(errors))


def _validate_native_benchmark_payload(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ["schema_version", "source", "backend", "results", "warnings"]:
        if key not in data:
            errors.append(f"missing required key: {key}")
    if data.get("source") != "android-native-microbench":
        errors.append("source must be android-native-microbench")
    if data.get("backend") != "cpu_android_native_reference":
        errors.append("backend must be cpu_android_native_reference")
    if "warnings" in data and not isinstance(data["warnings"], list):
        errors.append("warnings must be a list")

    results = data.get("results")
    if not isinstance(results, list):
        errors.append("results must be a list")
        return errors

    _, benchmark_errors = benchmark_results_from_payload(results)
    errors.extend(benchmark_errors)
    return errors


def _write_json(data: dict[str, Any], out_path: str | Path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out
