from pathlib import Path

import pytest

from qpnpu.android_logcat import (
    extract_phase8_external_model_json_from_logcat_file,
    extract_phase8_external_model_json_from_logcat_text,
    write_extracted_phase8_external_model_json,
)
from qpnpu.android_phase8 import validate_phase8_external_model


ROOT = Path(__file__).resolve().parents[1]


def test_extract_phase8_external_model_from_logcat_fixture(tmp_path: Path) -> None:
    logcat = ROOT / "tests" / "fixtures" / "android_phase8_logcat_smoke.txt"
    data = extract_phase8_external_model_json_from_logcat_file(logcat)

    assert validate_phase8_external_model(data) == []
    assert data["source"] == "android-phase8-external-model-demo"
    assert data["model_delivery"]["all_sha256_verified"] is True
    assert data["toy_decode"]["generated_token_ids"] == data["generated_token_ids"]

    out = write_extracted_phase8_external_model_json(logcat, tmp_path / "phase8.json")
    assert out.exists()


def test_extract_phase8_external_model_requires_begin_marker() -> None:
    with pytest.raises(ValueError, match="QPNPU_PHASE8_JSON_BEGIN"):
        extract_phase8_external_model_json_from_logcat_text("not a phase8 log")


def test_phase8_validator_rejects_unverified_delivery() -> None:
    logcat = ROOT / "tests" / "fixtures" / "android_phase8_logcat_smoke.txt"
    data = extract_phase8_external_model_json_from_logcat_file(logcat)
    data["model_delivery"]["all_sha256_verified"] = False

    errors = validate_phase8_external_model(data)

    assert any("all_sha256_verified" in error for error in errors)
