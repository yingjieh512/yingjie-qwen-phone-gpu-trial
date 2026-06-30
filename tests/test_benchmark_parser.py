from pathlib import Path

from qpnpu.benchmark import (
    minimal_benchmark_result,
    select_best_benchmarks,
    validate_benchmark_result,
)
from qpnpu.config import load_json, utc_now_iso


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


def test_embedded_toy_decode_benchmark_validates() -> None:
    payload = {
        "schema_version": "0.1",
        "timestamp_utc": utc_now_iso(),
        "source": "toy-runtime",
        "model": {
            "architecture": "qwen_toy",
            "hf_id": "local/toy-qwen-smoke",
            "hidden_size": 32,
            "num_layers": 1,
            "vocab_size": 256,
        },
        "backend": "cpu_python_reference",
        "prompt": "hello",
        "prompt_token_ids": [104, 101, 108, 108, 111],
        "generated_token_ids": [117, 123, 130, 138],
        "generated_text": "u{\\u0082\\u008a",
        "benchmark": {
            "schema_version": "0.1",
            "timestamp_utc": utc_now_iso(),
            "device": {"type": "local_host"},
            "model": {
                "architecture": "qwen_toy",
                "hf_id": "local/toy-qwen-smoke",
            },
            "backend": "cpu_python_reference",
            "operator": "toy_decode",
            "shape": {
                "max_new_tokens": 4,
                "hidden_size": 32,
                "vocab_size": 256,
            },
            "metrics": {
                "latency_ms_p50": 0.0,
                "latency_ms_p90": 0.0,
                "latency_ms_p99": 0.0,
                "tokens_per_second": 0.0,
                "memory_rss_mb": 0.0,
            },
            "thermal": {},
            "kernel_config_hash": "toy",
            "warnings": [],
        },
        "warnings": [
            "toy model only; not Qwen 9B",
            "local CPU Python reference only; not Android",
            "not NPU or QNN execution",
            "not a performance claim",
        ],
    }

    assert validate_benchmark_result(payload["benchmark"]) == []