from pathlib import Path

from qpnpu.adb_probe import (
    build_probe_result,
    parse_cpuinfo,
    parse_getprop,
    parse_gpu_probe,
    parse_meminfo,
    parse_npu_probe,
    recommended_backend_order,
)
from qpnpu.probe_schema import validate_probe_result


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "adb_probe"


def _fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_parse_getprop_extracts_device_and_soc_fields() -> None:
    parsed = parse_getprop(_fixture("raw_getprop.txt"))
    assert parsed["manufacturer"] == "SyntheticSamsung"
    assert parsed["model"] == "Synthetic Galaxy Probe"
    assert parsed["sdk"] == 36
    assert parsed["soc_manufacturer"] == "Qualcomm"
    assert parsed["soc_model"] == "Synthetic Snapdragon"
    assert parsed["supported_abis"] == ["arm64-v8a", "armeabi-v7a"]


def test_parse_cpuinfo_extracts_processor_count_and_features() -> None:
    parsed = parse_cpuinfo(_fixture("raw_cpuinfo.txt"))
    assert parsed["processor_count"] == 2
    assert "asimd" in parsed["features"]
    assert "0x51" in parsed["implementers"]
    assert parsed["hardware"] == "Qualcomm Technologies, Inc Synthetic"


def test_parse_meminfo_extracts_total_and_available() -> None:
    parsed = parse_meminfo(_fixture("raw_meminfo.txt"))
    assert parsed["mem_total_kb"] == 12000000
    assert parsed["mem_available_kb"] == 8000000
    assert parsed["swap_total_kb"] == 2000000


def test_parse_npu_probe_detects_qnn_libraries() -> None:
    parsed = parse_npu_probe(_fixture("raw_npu.txt"))
    assert parsed["qnn_libraries_detected"] is True
    assert "libQnnHtp.so" in parsed["qnn_libraries"]
    assert parsed["status"] == "hints_detected"


def test_parse_gpu_probe_detects_graphics_library_hints() -> None:
    parsed = parse_gpu_probe(_fixture("raw_gpu.txt"))
    assert parsed["vulkan_libraries_detected"] is True
    assert parsed["opencl_libraries_detected"] is True
    assert parsed["gles_libraries_detected"] is True
    assert parsed["adreno_hints"]


def test_build_probe_result_from_fixtures_validates() -> None:
    probe = build_probe_result(FIXTURE_DIR)
    assert validate_probe_result(probe) == []
    assert probe["source"] == "adb-host-probe"
    assert probe["microbenchmarks"]["phase1_note"]


def test_recommended_backend_order_from_fixture_is_conservative() -> None:
    probe = build_probe_result(FIXTURE_DIR)
    assert recommended_backend_order(probe) == ["qnn", "nnapi", "vulkan", "cpu"]

