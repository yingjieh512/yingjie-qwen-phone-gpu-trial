from pathlib import Path

from qpnpu.android_probe import read_android_probe
from qpnpu.hardware_characterization import (
    characterize_android_probe,
    render_hardware_model_markdown,
    validate_hardware_model,
    write_hardware_model_json,
    write_hardware_model_markdown,
)


ROOT = Path(__file__).resolve().parents[1]


def test_characterize_android_probe_fixture() -> None:
    probe = read_android_probe(ROOT / "tests" / "fixtures" / "android_probe_s26_smoke.json")
    model = characterize_android_probe(probe)

    assert validate_hardware_model(model) == []
    assert model["target"]["model"] == "SM-S948U1"
    assert model["target"]["soc_model"] == "SM8850"
    assert model["execution_model_neutral"] is True
    assert {unit["kind"] for unit in model["execution_units"]} >= {"cpu", "gpu", "npu_or_dsp_hint", "thermal"}
    assert "cpu_arm64_isa_feature_probe" in {item["id"] for item in model["fuzzing_plan"]}
    assert "backend_runtime_load_probe" in {item["id"] for item in model["fuzzing_plan"]}
    assert any("QNN availability" in gap for gap in model["probe_gaps"])


def test_render_and_write_hardware_model(tmp_path: Path) -> None:
    probe = read_android_probe(ROOT / "tests" / "fixtures" / "android_probe_s26_smoke.json")
    model = characterize_android_probe(probe)

    rendered = render_hardware_model_markdown(model)
    assert "Execution-Model-Neutral" in rendered
    assert "Structured Fuzzing Plan" in rendered

    out_json = write_hardware_model_json(tmp_path / "hardware_model.json", model)
    out_md = write_hardware_model_markdown(tmp_path / "hardware_model.md", model)
    assert out_json.exists()
    assert out_md.exists()
