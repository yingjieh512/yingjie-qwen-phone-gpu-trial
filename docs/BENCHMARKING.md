# Benchmarking

Benchmark artifacts are JSON records with enough context to avoid accidental performance claims.

## Benchmark Result Shape

```json
{
  "schema_version": "0.1",
  "timestamp_utc": "...",
  "device": {},
  "model": {},
  "backend": "cpu",
  "operator": "int4_matvec",
  "shape": {},
  "metrics": {
    "latency_ms_p50": 0.0,
    "latency_ms_p90": 0.0,
    "latency_ms_p99": 0.0,
    "tokens_per_second": 0.0,
    "memory_rss_mb": 0.0
  },
  "thermal": {},
  "kernel_config_hash": "sample",
  "warnings": []
}
```

## Phase 3 Toy Decode Benchmark

The toy decode smoke command writes a top-level result with an embedded benchmark object:

```bash
python scripts/model/run_toy_decode.py \
  --model-dir models/toy_qwen_smoke \
  --prompt "hello" \
  --max-new-tokens 8 \
  --out benchmarks/results/toy_decode_smoke.json
```

The embedded benchmark uses:

- `backend`: `cpu_python_reference`
- `operator`: `toy_decode`
- `device.type`: `local_host`
- `kernel_config_hash`: `toy`
- `shape.max_new_tokens`, `shape.hidden_size`, and `shape.vocab_size`

The top-level warnings state that the result is toy-only, not Qwen 9B, not Android, not NPU/QNN execution, and not a performance claim. The reported toy local CPU throughput is useful only for proving the JSON path and runtime plumbing work.

## Phase 2 Local CPU Microbenchmarks

The native microbenchmark executable measures local development-machine CPU operator latency only:

```bash
./native/build/qpnpu_microbench --operator int4_matvec --rows 256 --cols 256 --group-size 128 --iters 20 --out benchmarks/results/local_int4_matvec.json
```

The Python wrapper runs a small suite and writes a JSON list:

```bash
python scripts/native/run_local_microbench.py --build-dir native/build --out benchmarks/results/local_microbench.json
```

Each Phase 2 microbenchmark result includes this warning:

```text
local CPU microbenchmark; not a phone or NPU performance claim
```

Do not compare local desktop CPU operator timings or Phase 3 toy decode throughput against the phone/NPU target. Phase 3 does not run a full model decode benchmark.

Best-result selection groups by operator and shape, then chooses highest positive tokens/sec or lowest p50 latency when tokens/sec is missing or zero.