from pathlib import Path

from qpnpu.benchmark import (
    minimal_benchmark_result,
    select_best_benchmarks,
    validate_benchmark_result,
)
from qpnpu.config import load_json


ROOT = Path(__file__).resolve().parents[1]


def test_minimal_benchmark_validates() -> None:
    assert validate_benchmark_result(minimal_benchmark_result()) == []


def test_best_benchmark_selection_picks_highest_tokens_per_second() -> None:
    slower = minimal_benchmark_result()
    faster = minimal_benchmark_result()
    slower["shape"] = {"m": 1, "n": 64, "k": 128}
    faster["shape"] = {"m": 1, "n": 64, "k": 128}
    slower["metrics"]["tokens_per_second"] = 10.0
    faster["metrics"]["tokens_per_second"] = 12.0

    selected = select_best_benchmarks([slower, faster])
    assert len(selected) == 1
    assert next(iter(selected.values()))["metrics"]["tokens_per_second"] == 12.0


def test_sample_benchmark_validates() -> None:
    sample = load_json(ROOT / "benchmarks" / "results" / "sample_benchmark.json")
    assert validate_benchmark_result(sample) == []

