from qpnpu.benchmark import benchmark_results_from_payload, minimal_benchmark_result, select_best_benchmarks


def test_benchmark_results_from_single_object() -> None:
    result = minimal_benchmark_result()
    results, errors = benchmark_results_from_payload(result)
    assert errors == []
    assert results == [result]


def test_benchmark_results_from_list_and_latency_fallback() -> None:
    slow = minimal_benchmark_result()
    fast = minimal_benchmark_result()
    slow["shape"] = {"n": 128}
    fast["shape"] = {"n": 128}
    slow["metrics"]["tokens_per_second"] = 0.0
    fast["metrics"]["tokens_per_second"] = 0.0
    slow["metrics"]["latency_ms_p50"] = 2.0
    fast["metrics"]["latency_ms_p50"] = 1.0

    results, errors = benchmark_results_from_payload([slow, fast])
    assert errors == []
    selected = select_best_benchmarks(results)
    assert next(iter(selected.values()))["metrics"]["latency_ms_p50"] == 1.0