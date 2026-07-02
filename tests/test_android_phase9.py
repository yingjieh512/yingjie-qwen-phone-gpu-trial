from pathlib import Path

import pytest

from qpnpu.android_logcat import (
    extract_phase9_native_shard_loader_json_from_logcat_file,
    extract_phase9_native_shard_loader_json_from_logcat_text,
    write_extracted_phase9_native_shard_loader_json,
)
from qpnpu.android_phase9 import validate_phase9_native_shard_loader


ROOT = Path(__file__).resolve().parents[1]


def test_extract_phase9_native_shard_loader_from_logcat_fixture(tmp_path: Path) -> None:
    logcat = ROOT / "tests" / "fixtures" / "android_phase9_logcat_smoke.txt"
    data = extract_phase9_native_shard_loader_json_from_logcat_file(logcat)

    assert validate_phase9_native_shard_loader(data) == []
    assert data["source"] == "android-phase9-native-shard-loader"
    assert data["native_model_loader"]["open_method"] == "mmap_readonly"
    assert data["native_model_loader"]["java_tensor_bytes_passed"] is False
    assert data["toy_decode"]["generated_token_ids"] == data["generated_token_ids"]

    out = write_extracted_phase9_native_shard_loader_json(logcat, tmp_path / "phase9.json")
    assert out.exists()


def test_extract_phase9_native_shard_loader_requires_begin_marker() -> None:
    with pytest.raises(ValueError, match="QPNPU_PHASE9_JSON_BEGIN"):
        extract_phase9_native_shard_loader_json_from_logcat_text("not a phase9 log")


def test_phase9_validator_rejects_java_tensor_bytes() -> None:
    logcat = ROOT / "tests" / "fixtures" / "android_phase9_logcat_smoke.txt"
    data = extract_phase9_native_shard_loader_json_from_logcat_file(logcat)
    data["native_model_loader"]["java_tensor_bytes_passed"] = True

    errors = validate_phase9_native_shard_loader(data)

    assert any("java_tensor_bytes_passed" in error for error in errors)
