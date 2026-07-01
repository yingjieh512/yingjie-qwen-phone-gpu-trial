"""Extract QPNPU Android probe JSON from logcat text."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from qpnpu.probe_schema import validate_probe_result


LOGCAT_MESSAGE_RE = re.compile(r"^.*?\s[VDIWEF]\sQPNPUProbe:\s?(.*)$")
BEGIN_MARKER = "QPNPU_PROBE_JSON_BEGIN"
END_MARKER = "QPNPU_PROBE_JSON_END"


def extract_probe_json_from_logcat_text(text: str) -> dict[str, Any]:
    """Extract and validate probe JSON emitted between QPNPU logcat markers."""

    chunks: list[str] = []
    inside = False
    saw_begin = False
    saw_end = False

    for line in text.splitlines():
        match = LOGCAT_MESSAGE_RE.match(line)
        if not match:
            continue
        message = match.group(1)
        if BEGIN_MARKER in message:
            inside = True
            saw_begin = True
            continue
        if END_MARKER in message:
            saw_end = True
            break
        if inside:
            chunks.append(message)

    if not saw_begin:
        raise ValueError(f"missing {BEGIN_MARKER}")
    if not saw_end:
        raise ValueError(f"missing {END_MARKER}")
    if not chunks:
        raise ValueError("no QPNPU probe JSON chunks found")

    errors: list[str] = []
    for separator in ("", "\n"):
        candidate = separator.join(chunks)
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError as exc:
            errors.append(str(exc))
            continue
        validation_errors = validate_probe_result(data)
        if validation_errors:
            raise ValueError("invalid extracted probe JSON: " + "; ".join(validation_errors))
        return data

    raise ValueError("failed to parse QPNPU probe JSON from logcat chunks: " + " | ".join(errors))


def extract_probe_json_from_logcat_file(path: str | Path) -> dict[str, Any]:
    """Read a logcat text file and extract the probe JSON object."""

    return extract_probe_json_from_logcat_text(Path(path).read_text(encoding="utf-8"))


def write_extracted_probe_json(logcat_path: str | Path, out_path: str | Path) -> Path:
    """Extract probe JSON from a logcat file and write pretty JSON."""

    data = extract_probe_json_from_logcat_file(logcat_path)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out
