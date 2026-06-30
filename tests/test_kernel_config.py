from pathlib import Path

from qpnpu.config import load_json
from qpnpu.kernel_config import kernel_config_hash, validate_kernel_config


ROOT = Path(__file__).resolve().parents[1]


def test_example_kernel_config_validates() -> None:
    config = load_json(ROOT / "configs" / "kernel_config.example.json")
    assert validate_kernel_config(config) == []


def test_kernel_config_hash_is_deterministic() -> None:
    config = load_json(ROOT / "configs" / "kernel_config.example.json")
    assert kernel_config_hash(config) == kernel_config_hash(dict(reversed(list(config.items()))))

