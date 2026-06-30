# Benchmarking

Benchmark artifacts must be explicit JSON records with enough context to avoid accidental performance claims.

Result shape:

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

Phase 0 status:

- Sample benchmark data is clearly marked as sample-only.
- `tokens_per_second` is `0.0` in the sample artifact.
- No performance claims are made.
- Best-result selection groups by operator and shape, then chooses highest positive tokens/sec or lowest p50 latency.

