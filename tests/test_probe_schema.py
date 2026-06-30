from pathlib import Path

from qpnpu.config import load_json
from qpnpu.probe_schema import minimal_probe_result, validate_probe_result


ROOT = Path(__file__).resolve().parents[1]


def test_minimal_probe_validates() -> None:
    assert validate_probe_result(minimal_probe_result()) == []


def test_missing_required_probe_fields_produces_errors() -> None:
    errors = validate_probe_result({"schema_version": "0.1"})
    assert errors
    assert any("timestamp_utc" in error for error in errors)


def test_sample_probe_validates() -> None:
    sample = load_json(ROOT / "benchmarks" / "results" / "sample_probe.json")
    assert validate_probe_result(sample) == []

