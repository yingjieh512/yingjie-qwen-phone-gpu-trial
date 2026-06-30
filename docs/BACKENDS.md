# Backends

Backend selection must be driven by runtime probe data. The trial input mentions a Snapdragon-class NPU, but Phase 0 does not assume QNN, NNAPI, Vulkan, or direct NPU access is available.

Planned backend roles:

- CPU: reference backend and guaranteed fallback.
- Vulkan: planned compute backend stub for future GPU experiments.
- NNAPI: planned Android accelerator API probe and execution path.
- QNN: planned Qualcomm backend stub, enabled only if device and SDK support are present.

Phase 0 status:

- No NPU execution is implemented.
- No Qualcomm SDK is required.
- No NNAPI or Vulkan execution is implemented.
- Native directories are placeholders for later phases.

