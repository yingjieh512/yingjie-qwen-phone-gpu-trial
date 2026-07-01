from pathlib import Path

from qpnpu.android_probe import (
    read_android_probe,
    render_android_probe_summary,
    summarize_android_probe,
    write_summary_json,
    write_summary_markdown,
)


ROOT = Path(__file__).resolve().parents[1]


def test_summarize_android_probe_fixture() -> None:
    probe = read_android_probe(ROOT / "tests" / "fixtures" / "android_probe_s26_smoke.json")
    summary = summarize_android_probe(probe)

    assert summary["device"]["model"] == "SM-S948U1"
    assert summary["device"]["soc_model"] == "SM8850"
    assert summary["cpu"]["available_processors"] == 8
    assert summary["memory"]["mem_total_kb"] == 11389632
    assert summary["gpu"]["status"] == "hints_detected"
    assert summary["gpu"]["vulkan_libraries_detected"] is False
    assert summary["npu"]["status"] == "hints_detected"
    assert summary["npu"]["qnn_libraries_detected"] is False
    assert summary["thermal"]["zone_count"] == 3
    assert any("not proof" in item or "not proven" in item for item in summary["interpretation"])


def test_render_and_write_android_probe_summary(tmp_path: Path) -> None:
    probe = read_android_probe(ROOT / "tests" / "fixtures" / "android_probe_s26_smoke.json")
    summary = summarize_android_probe(probe)

    rendered = render_android_probe_summary(summary)
    assert "SM-S948U1" in rendered
    assert "qnn_libraries_detected=False" in rendered

    out_json = write_summary_json(tmp_path / "summary.json", summary)
    out_md = write_summary_markdown(tmp_path / "profile.md", summary)
    assert out_json.exists()
    assert out_md.exists()
    assert "Target Hardware Profile" in out_md.read_text(encoding="utf-8")
