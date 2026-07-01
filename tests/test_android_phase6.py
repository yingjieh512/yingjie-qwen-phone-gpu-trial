from pathlib import Path

import pytest

from qpnpu.android_logcat import (
    PHASE6_BEGIN_MARKER,
    extract_phase6_characterization_json_from_logcat_file,
    extract_phase6_characterization_json_from_logcat_text,
    write_extracted_phase6_characterization_json,
)
from qpnpu.android_phase6 import validate_phase6_characterization


ROOT = Path(__file__).resolve().parents[1]


def test_extract_phase6_characterization_from_logcat_fixture(tmp_path: Path) -> None:
    logcat = ROOT / "tests" / "fixtures" / "android_phase6_logcat_smoke.txt"
    data = extract_phase6_characterization_json_from_logcat_file(logcat)

    assert validate_phase6_characterization(data) == []
    assert data["source"] == "android-phase6-characterization"
    assert data["backend"] == "cpu_android_native_reference"
    assert data["cpu_isa"]["features"][0]["name"] == "i8mm"
    assert data["backend_load"]["probes"][0]["backend"] == "vulkan"
    assert data["quantization"]["fixtures"][0]["correctness_passed"] is True

    out = write_extracted_phase6_characterization_json(logcat, tmp_path / "phase6.json")
    assert out.exists()


def test_extract_phase6_characterization_requires_begin_marker() -> None:
    with pytest.raises(ValueError, match=PHASE6_BEGIN_MARKER):
        extract_phase6_characterization_json_from_logcat_text("not a phase6 log")


def test_phase6_validator_rejects_failed_quant_fixture() -> None:
    data = extract_phase6_characterization_json_from_logcat_file(
        ROOT / "tests" / "fixtures" / "android_phase6_logcat_smoke.txt"
    )
    data["quantization"]["fixtures"][0]["correctness_passed"] = False

    assert any("did not pass correctness" in error for error in validate_phase6_characterization(data))
