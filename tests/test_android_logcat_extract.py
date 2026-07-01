from pathlib import Path

import pytest

from qpnpu.android_logcat import (
    BEGIN_MARKER,
    extract_all_qpnpu_json_from_logcat_text,
    extract_probe_json_from_logcat_file,
    extract_probe_json_from_logcat_text,
    write_extracted_probe_json,
)


ROOT = Path(__file__).resolve().parents[1]


def test_extract_probe_json_from_logcat_fixture(tmp_path: Path) -> None:
    logcat = ROOT / "tests" / "fixtures" / "android_probe_logcat_smoke.txt"
    data = extract_probe_json_from_logcat_file(logcat)

    assert data["source"] == "android-probe-app"
    assert data["device"]["model"] == "SM-S948U1"

    out = write_extracted_probe_json(logcat, tmp_path / "probe.json")
    assert out.exists()


def test_extract_probe_json_requires_begin_marker() -> None:
    with pytest.raises(ValueError, match=BEGIN_MARKER):
        extract_probe_json_from_logcat_text("not a probe log")


def test_extract_all_qpnpu_json_from_combined_logcat_fixtures() -> None:
    fixture_dir = ROOT / "tests" / "fixtures"
    combined = "\n".join(
        [
            (fixture_dir / "android_probe_logcat_smoke.txt").read_text(encoding="utf-8"),
            (fixture_dir / "android_native_microbench_logcat_smoke.txt").read_text(encoding="utf-8"),
            (fixture_dir / "android_phase6_logcat_smoke.txt").read_text(encoding="utf-8"),
            (fixture_dir / "android_phase7a_logcat_smoke.txt").read_text(encoding="utf-8"),
            (fixture_dir / "android_phase7c_logcat_smoke.txt").read_text(encoding="utf-8"),
            (fixture_dir / "android_toy_decode_logcat_smoke.txt").read_text(encoding="utf-8"),
        ]
    )

    data = extract_all_qpnpu_json_from_logcat_text(combined)

    assert data["payload_count"] == 6
    assert data["counts"] == {
        "probe": 1,
        "native": 1,
        "phase6": 1,
        "phase7a": 1,
        "phase7c": 1,
        "toy_decode": 1,
    }
    assert [item["kind"] for item in data["payloads"]] == [
        "probe",
        "native",
        "phase6",
        "phase7a",
        "phase7c",
        "toy_decode",
    ]