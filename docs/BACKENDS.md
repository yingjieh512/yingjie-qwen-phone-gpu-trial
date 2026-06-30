# Backends

Backend selection must be driven by runtime probe data. The trial input mentions a Snapdragon-class NPU, but this repository must not assume QNN, NNAPI, Vulkan, or direct NPU access is available.

## Phase 2 Status

- CPU: implemented as a local reference backend for correctness and operator microbench scaffolding.
- Vulkan: safe unavailable stub only.
- NNAPI: safe unavailable stub only; Android native/app work is required before any real NNAPI enumeration or execution.
- QNN: safe unavailable stub only; Qualcomm QNN SDK/runtime is not integrated.

No NPU execution is implemented in Phase 2.

## CPU Reference Backend

The CPU backend reports available and calls reference implementations for:

- fp32 matvec
- groupwise symmetric int4 dequant matvec
- RMSNorm
- RoPE
- softmax

These kernels are intentionally simple and are meant for correctness checks and future backend comparison, not optimized production inference.

## Stub Backend Rules

Vulkan, NNAPI, and QNN backends must return unavailable and provide a non-empty reason. They must not pretend to execute kernels or imply accelerator support.