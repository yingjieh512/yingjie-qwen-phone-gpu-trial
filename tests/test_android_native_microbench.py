from pathlib import Path

import pytest

from qpnpu.android_logcat import (
    NATIVE_BENCH_BEGIN_MARKER,
    extract_native_benchmark_json_from_logcat_file,
    extract_native_benchmark_json_from_logcat_text,
    write_extracted_native_benchmark_json,
)
from qpnpu.benchmark import validate_benchmark_result


ROOT = Path(__file__).resolve().parents[1]


def test_extract_native_microbenchmarks_from_logcat_fixture(tmp_path: Path) -> None:
    logcat = ROOT / "tests" / "fixtures" / "android_native_microbench_logcat_smoke.txt"
    data = extract_native_benchmark_json_from_logcat_file(logcat)

    assert data["source"] == "android-native-microbench"
    assert data["backend"] == "cpu_android_native_reference"
    assert data["available"] is True
    assert data["all_correctness_passed"] is True
    assert {result["operator"] for result in data["results"]} == {
        "fp32_matvec",
        "int4_dequant_matvec",
        "rmsnorm",
        "softmax",
        "rope",
    }
    assert any("not a performance target claim" in warning for warning in data["warnings"])

    for result in data["results"]:
        assert validate_benchmark_result(result) == []
        assert result["metrics"]["correctness_passed"] is True
        assert any("not a performance claim" in warning for warning in result["warnings"])

    out = write_extracted_native_benchmark_json(logcat, tmp_path / "native.json")
    assert out.exists()


def test_extract_native_microbenchmarks_requires_begin_marker() -> None:
    with pytest.raises(ValueError, match=NATIVE_BENCH_BEGIN_MARKER):
        extract_native_benchmark_json_from_logcat_text("not a native benchmark log")
