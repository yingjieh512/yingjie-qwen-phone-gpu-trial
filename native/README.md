# Native Runtime Foundation

Phase 2 provides a small C++17 native foundation:

- tensor view helpers
- CPU reference kernels
- backend interface
- CPU backend implementation
- Vulkan, NNAPI, and QNN unavailable stubs
- CTest correctness tests
- local CPU microbenchmark executable

Build and test:

```bash
cmake -S native -B native/build
cmake --build native/build
ctest --test-dir native/build --output-on-failure
```

No Android device, Qualcomm SDK, AWS credentials, or model weights are required.