# Performance Targets

The long-term trial target is at least 20 decode tokens/sec for the configurable Qwen-style 9B decoder model on the target Android phone class.

Current status:

- The target remains unmeasured.
- No full model execution exists.
- No on-device benchmark has run.
- No NPU execution exists.
- No performance target is claimed as achieved.

## Phase 2 Measurements

Phase 2 can measure local development-machine CPU operator microbenchmarks for reference kernels. These measurements are useful for checking benchmark plumbing and rough local regressions only.

They are not:

- phone results
- NPU results
- QNN results
- full-model decode results
- evidence that the 20 decode tokens/sec target has been met

Future performance claims must include device probe data, backend used, model metadata, context/decode lengths, thermal state, and raw benchmark JSON artifacts.