from pathlib import Path

import pytest

from qpnpu.android_logcat import (
    TOY_DECODE_BEGIN_MARKER,
    extract_android_toy_decode_json_from_logcat_file,
    extract_android_toy_decode_json_from_logcat_text,
    write_extracted_android_toy_decode_json,
)
from qpnpu.android_toy_decode import validate_android_toy_decode


ROOT = Path(__file__).resolve().parents[1]


def test_extract_android_toy_decode_from_logcat_fixture(tmp_path: Path) -> None:
    logcat = ROOT / "tests" / "fixtures" / "android_toy_decode_logcat_smoke.txt"
    data = extract_android_toy_decode_json_from_logcat_file(logcat)

    assert validate_android_toy_decode(data) == []
    assert data["source"] == "android-toy-decode"
    assert data["backend"] == "cpu_android_native_reference"
    assert data["model"]["architecture"] == "qwen_toy"
    assert data["tokenizer"]["is_qwen_tokenizer"] is False
    assert data["decode"]["max_new_tokens"] == 4
    assert len(data["generated_token_ids"]) == 4
    assert data["benchmark"]["operator"] == "toy_decode"
    assert any("not Qwen 9B" in warning for warning in data["warnings"])

    out = write_extracted_android_toy_decode_json(logcat, tmp_path / "toy_decode.json")
    assert out.exists()


def test_extract_android_toy_decode_requires_begin_marker() -> None:
    with pytest.raises(ValueError, match=TOY_DECODE_BEGIN_MARKER):
        extract_android_toy_decode_json_from_logcat_text("not a toy decode log")


def test_android_toy_decode_validator_rejects_inconsistent_length() -> None:
    data = extract_android_toy_decode_json_from_logcat_file(
        ROOT / "tests" / "fixtures" / "android_toy_decode_logcat_smoke.txt"
    )
    data["decode"]["max_new_tokens"] = 99

    assert any("generated_token_ids length" in error for error in validate_android_toy_decode(data))