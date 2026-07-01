# Performance Targets

The long-term trial target is at least 20 decode tokens/sec for the configurable Qwen-style 9B decoder model on the target Android phone class.

Current status:

- The target remains unmeasured.
- No full model execution exists.
- No full-model on-device benchmark has run.
- No NPU execution exists.
- No performance target is claimed as achieved.

## Phase 6 Characterization

Phase 6 can report thread-scaling and memory-copy timings plus backend library load statuses. These are hardware characterization signals only.

They are not:

- Qwen 9B inference
- accelerator execution
- QNN, NNAPI, or Vulkan kernel execution
- full-model decode results
- comparable to the `>=20 decode tokens/sec` target
- evidence that the target has been met
## Phase 5 Android Native CPU Microbenchmarks

Phase 5 can run tiny native CPU fixtures inside the Android APK. These measurements are useful for validating ABI packaging, JNI calls, native timing, correctness checks, and JSON extraction on a real phone.

They are not:

- Qwen 9B inference
- NPU results
- QNN results
- full-model decode results
- comparable to the `>=20 decode tokens/sec` target
- evidence that the target has been met
## Phase 3 Toy Local Throughput

Phase 3 can report tokens/sec for a tiny local CPU Python toy decode. That number is only a smoke-test timing for a 32-hidden-size byte-token toy artifact.

It is not comparable to the target because it is not:

- Qwen 9B
- a real transformer decode
- Android execution
- NPU execution
- QNN execution
- a full-model benchmark
- evidence that the 20 decode tokens/sec target has been met

The `>=20 decode tokens/sec` target remains unmeasured.

## Phase 2 Measurements

Phase 2 can measure local development-machine CPU operator microbenchmarks for reference kernels. These measurements are useful for checking benchmark plumbing and rough local regressions only.

They are not:

- phone results
- NPU results
- QNN results
- full-model decode results
- evidence that the 20 decode tokens/sec target has been met

Future performance claims must include device probe data, backend used, model metadata, context/decode lengths, thermal state, and raw benchmark JSON artifacts.