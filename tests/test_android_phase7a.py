from pathlib import Path

import pytest

from qpnpu.android_logcat import (
    PHASE7A_BEGIN_MARKER,
    extract_phase7a_isa_probes_json_from_logcat_file,
    extract_phase7a_isa_probes_json_from_logcat_text,
    write_extracted_phase7a_isa_probes_json,
)
from qpnpu.android_phase7a import validate_phase7a_isa_probes


ROOT = Path(__file__).resolve().parents[1]


def test_extract_phase7a_isa_probes_from_logcat_fixture(tmp_path: Path) -> None:
    logcat = ROOT / "tests" / "fixtures" / "android_phase7a_logcat_smoke.txt"
    data = extract_phase7a_isa_probes_json_from_logcat_file(logcat)

    assert validate_phase7a_isa_probes(data) == []
    assert data["source"] == "android-phase7a-isa-probes"
    assert data["backend"] == "cpu_android_native_reference"
    assert data["safety"]["strategy"] == "sigaction_sigsetjmp_same_process"
    assert data["isa_probes"][0]["feature_name"] == "asimd"
    assert data["isa_probes"][0]["status"] == "executed_ok"
    assert data["summary"]["probe_count"] == 2

    out = write_extracted_phase7a_isa_probes_json(logcat, tmp_path / "phase7a.json")
    assert out.exists()


def test_extract_phase7a_isa_probes_requires_begin_marker() -> None:
    with pytest.raises(ValueError, match=PHASE7A_BEGIN_MARKER):
        extract_phase7a_isa_probes_json_from_logcat_text("not a phase7a log")


def test_phase7a_validator_rejects_inconsistent_summary() -> None:
    data = extract_phase7a_isa_probes_json_from_logcat_file(
        ROOT / "tests" / "fixtures" / "android_phase7a_logcat_smoke.txt"
    )
    data["summary"]["probe_count"] = 999

    assert any("probe_count" in error for error in validate_phase7a_isa_probes(data))