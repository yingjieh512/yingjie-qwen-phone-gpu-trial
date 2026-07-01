"""Extract QPNPU Android JSON payloads from logcat text."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from qpnpu.android_phase6 import validate_phase6_characterization
from qpnpu.android_phase7a import validate_phase7a_isa_probes
from qpnpu.benchmark import benchmark_results_from_payload
from qpnpu.probe_schema import validate_probe_result


LOGCAT_MESSAGE_RE = re.compile(r"^.*?\s[VDIWEF]\sQPNPUProbe:\s?(.*)$")
BEGIN_MARKER = "QPNPU_PROBE_JSON_BEGIN"
END_MARKER = "QPNPU_PROBE_JSON_END"
NATIVE_BENCH_BEGIN_MARKER = "QPNPU_NATIVE_BENCH_JSON_BEGIN"
NATIVE_BENCH_END_MARKER = "QPNPU_NATIVE_BENCH_JSON_END"
PHASE6_BEGIN_MARKER = "QPNPU_PHASE6_JSON_BEGIN"
PHASE6_END_MARKER = "QPNPU_PHASE6_JSON_END"
PHASE7A_BEGIN_MARKER = "QPNPU_PHASE7A_JSON_BEGIN"
PHASE7A_END_MARKER = "QPNPU_PHASE7A_JSON_END"


_MARKER_SPECS = [
    ("probe", BEGIN_MARKER, END_MARKER),
    ("native", NATIVE_BENCH_BEGIN_MARKER, NATIVE_BENCH_END_MARKER),
    ("phase6", PHASE6_BEGIN_MARKER, PHASE6_END_MARKER),
    ("phase7a", PHASE7A_BEGIN_MARKER, PHASE7A_END_MARKER),
]


def extract_probe_json_from_logcat_text(text: str) -> dict[str, Any]:
    """Extract and validate the first probe JSON emitted between QPNPU logcat markers."""

    data = _extract_json_with_markers(text, BEGIN_MARKER, END_MARKER)
    validation_errors = validate_probe_result(data)
    if validation_errors:
        raise ValueError("invalid extracted probe JSON: " + "; ".join(validation_errors))
    return data


def extract_probe_json_from_logcat_file(path: str | Path) -> dict[str, Any]:
    """Read a logcat text file and extract the first probe JSON object."""

    return extract_probe_json_from_logcat_text(Path(path).read_text(encoding="utf-8"))


def write_extracted_probe_json(logcat_path: str | Path, out_path: str | Path) -> Path:
    """Extract probe JSON from a logcat file and write pretty JSON."""

    data = extract_probe_json_from_logcat_file(logcat_path)
    return _write_json(data, out_path)


def extract_native_benchmark_json_from_logcat_text(text: str) -> dict[str, Any]:
    """Extract and validate the first native microbenchmark JSON from QPNPU logcat markers."""

    data = _extract_json_with_markers(text, NATIVE_BENCH_BEGIN_MARKER, NATIVE_BENCH_END_MARKER)
    validation_errors = _validate_native_benchmark_payload(data)
    if validation_errors:
        raise ValueError("invalid extracted native benchmark JSON: " + "; ".join(validation_errors))
    return data


def extract_native_benchmark_json_from_logcat_file(path: str | Path) -> dict[str, Any]:
    """Read a logcat text file and extract the first native microbenchmark JSON object."""

    return extract_native_benchmark_json_from_logcat_text(Path(path).read_text(encoding="utf-8"))


def write_extracted_native_benchmark_json(logcat_path: str | Path, out_path: str | Path) -> Path:
    """Extract native microbenchmark JSON from logcat and write pretty JSON."""

    data = extract_native_benchmark_json_from_logcat_file(logcat_path)
    return _write_json(data, out_path)


def extract_phase6_characterization_json_from_logcat_text(text: str) -> dict[str, Any]:
    """Extract and validate the first Phase 6 characterization JSON from QPNPU logcat markers."""

    data = _extract_json_with_markers(text, PHASE6_BEGIN_MARKER, PHASE6_END_MARKER)
    validation_errors = validate_phase6_characterization(data)
    if validation_errors:
        raise ValueError("invalid extracted Phase 6 characterization JSON: " + "; ".join(validation_errors))
    return data


def extract_phase6_characterization_json_from_logcat_file(path: str | Path) -> dict[str, Any]:
    """Read a logcat text file and extract the first Phase 6 characterization JSON object."""

    return extract_phase6_characterization_json_from_logcat_text(Path(path).read_text(encoding="utf-8"))


def write_extracted_phase6_characterization_json(logcat_path: str | Path, out_path: str | Path) -> Path:
    """Extract Phase 6 characterization JSON from logcat and write pretty JSON."""

    data = extract_phase6_characterization_json_from_logcat_file(logcat_path)
    return _write_json(data, out_path)



def extract_phase7a_isa_probes_json_from_logcat_text(text: str) -> dict[str, Any]:
    """Extract and validate the first Phase 7A guarded ISA probe JSON from QPNPU logcat markers."""

    data = _extract_json_with_markers(text, PHASE7A_BEGIN_MARKER, PHASE7A_END_MARKER)
    validation_errors = validate_phase7a_isa_probes(data)
    if validation_errors:
        raise ValueError("invalid extracted Phase 7A ISA probe JSON: " + "; ".join(validation_errors))
    return data


def extract_phase7a_isa_probes_json_from_logcat_file(path: str | Path) -> dict[str, Any]:
    """Read a logcat text file and extract the first Phase 7A guarded ISA probe JSON object."""

    return extract_phase7a_isa_probes_json_from_logcat_text(Path(path).read_text(encoding="utf-8"))


def write_extracted_phase7a_isa_probes_json(logcat_path: str | Path, out_path: str | Path) -> Path:
    """Extract Phase 7A guarded ISA probe JSON from logcat and write pretty JSON."""

    data = extract_phase7a_isa_probes_json_from_logcat_file(logcat_path)
    return _write_json(data, out_path)

def extract_all_qpnpu_json_from_logcat_text(text: str) -> dict[str, Any]:
    """Extract every valid QPNPU probe/native/Phase 6/Phase 7A payload from logcat text."""

    payloads: list[dict[str, Any]] = []
    active_kind = ""
    active_end_marker = ""
    chunks: list[str] = []

    for line in text.splitlines():
        match = LOGCAT_MESSAGE_RE.match(line)
        if not match:
            continue
        message = match.group(1)

        if active_kind:
            if active_end_marker in message:
                data = _parse_qpnpu_json_chunks(chunks)
                validation_errors = _validate_payload_by_kind(active_kind, data)
                if validation_errors:
                    raise ValueError(
                        f"invalid extracted {active_kind} JSON: " + "; ".join(validation_errors)
                    )
                payloads.append({"kind": active_kind, "payload": data})
                active_kind = ""
                active_end_marker = ""
                chunks = []
            else:
                chunks.append(message)
            continue

        for kind, begin_marker, end_marker in _MARKER_SPECS:
            if begin_marker in message:
                active_kind = kind
                active_end_marker = end_marker
                chunks = []
                break

    if active_kind:
        raise ValueError(f"missing {active_end_marker}")
    if not payloads:
        raise ValueError("missing QPNPU JSON markers")

    counts = {"probe": 0, "native": 0, "phase6": 0, "phase7a": 0}
    for item in payloads:
        counts[item["kind"]] += 1

    return {
        "schema_version": "0.1",
        "source": "android-logcat-extraction",
        "payload_count": len(payloads),
        "counts": counts,
        "payloads": payloads,
    }


def extract_all_qpnpu_json_from_logcat_file(path: str | Path) -> dict[str, Any]:
    """Read a logcat text file and extract every valid QPNPU payload."""

    return extract_all_qpnpu_json_from_logcat_text(Path(path).read_text(encoding="utf-8"))


def write_all_qpnpu_json_from_logcat(logcat_path: str | Path, out_path: str | Path) -> Path:
    """Extract every QPNPU payload from logcat and write a bundled JSON artifact."""

    data = extract_all_qpnpu_json_from_logcat_file(logcat_path)
    return _write_json(data, out_path)


def _extract_json_with_markers(text: str, begin_marker: str, end_marker: str) -> dict[str, Any]:
    blocks = _extract_json_blocks_with_markers(text, begin_marker, end_marker)
    return blocks[0]


def _extract_json_blocks_with_markers(text: str, begin_marker: str, end_marker: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    chunks: list[str] = []
    inside = False
    saw_begin = False

    for line in text.splitlines():
        match = LOGCAT_MESSAGE_RE.match(line)
        if not match:
            continue
        message = match.group(1)
        if begin_marker in message:
            inside = True
            saw_begin = True
            chunks = []
            continue
        if end_marker in message and inside:
            blocks.append(_parse_qpnpu_json_chunks(chunks))
            inside = False
            chunks = []
            continue
        if inside:
            chunks.append(message)

    if inside:
        raise ValueError(f"missing {end_marker}")
    if not saw_begin:
        raise ValueError(f"missing {begin_marker}")
    if not blocks:
        raise ValueError("no QPNPU JSON chunks found")
    return blocks


def _parse_qpnpu_json_chunks(chunks: list[str]) -> dict[str, Any]:
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


def _validate_payload_by_kind(kind: str, data: dict[str, Any]) -> list[str]:
    if kind == "probe":
        return validate_probe_result(data)
    if kind == "native":
        return _validate_native_benchmark_payload(data)
    if kind == "phase6":
        return validate_phase6_characterization(data)
    if kind == "phase7a":
        return validate_phase7a_isa_probes(data)
    return [f"unknown QPNPU payload kind: {kind}"]


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
