from pathlib import Path

import pytest

from qpnpu.android_logcat import (
    PHASE7C_BEGIN_MARKER,
    extract_phase7c_generated_kernels_json_from_logcat_file,
    extract_phase7c_generated_kernels_json_from_logcat_text,
    write_extracted_phase7c_generated_kernels_json,
)
from qpnpu.android_phase7c import validate_phase7c_generated_kernels


ROOT = Path(__file__).resolve().parents[1]


def test_extract_phase7c_generated_kernels_from_logcat_fixture(tmp_path: Path) -> None:
    logcat = ROOT / "tests" / "fixtures" / "android_phase7c_logcat_smoke.txt"
    data = extract_phase7c_generated_kernels_json_from_logcat_file(logcat)

    assert validate_phase7c_generated_kernels(data) == []
    assert data["source"] == "android-phase7c-generated-kernels"
    assert data["backend"] == "cpu_android_generated_candidate"
    assert data["safety"]["uses_sigill_guard"] is True
    assert data["summary"] == {
        "candidate_count": 3,
        "executed_count": 1,
        "passed_count": 1,
        "sigill_count": 0,
        "skipped_count": 1,
        "deferred_count": 1,
        "experimental_count": 1,
        "all_executed_correctness_passed": True,
    }
    assert data["candidates"][0]["status"] == "passed_correctness"
    assert data["candidates"][1]["status"] == "skipped_feature_not_reported"
    assert data["candidates"][2]["status"] == "deferred_no_safe_kernel"

    out = write_extracted_phase7c_generated_kernels_json(logcat, tmp_path / "phase7c.json")
    assert out.exists()


def test_extract_phase7c_generated_kernels_requires_begin_marker() -> None:
    with pytest.raises(ValueError, match=PHASE7C_BEGIN_MARKER):
        extract_phase7c_generated_kernels_json_from_logcat_text("not a phase7c log")


def test_phase7c_validator_rejects_bad_summary() -> None:
    data = extract_phase7c_generated_kernels_json_from_logcat_file(
        ROOT / "tests" / "fixtures" / "android_phase7c_logcat_smoke.txt"
    )
    data["summary"]["executed_count"] = 99

    assert any("summary.executed_count" in error for error in validate_phase7c_generated_kernels(data))