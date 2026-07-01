from pathlib import Path

import pytest

from qpnpu.android_logcat import (
    BEGIN_MARKER,
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
