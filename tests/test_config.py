from pathlib import Path

from qpnpu.config import load_yaml


ROOT = Path(__file__).resolve().parents[1]


def test_trial_config_target_and_backends() -> None:
    config = load_yaml(ROOT / "configs" / "trial.yaml")
    assert config["runtime"]["target_decode_tps"] == 20
    assert "cpu" in config["runtime"]["preferred_backends"]

