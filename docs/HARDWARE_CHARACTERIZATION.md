# Execution-Model-Neutral Hardware Characterization

This document is a conservative hardware model generated from Android probe evidence. It is not a performance report.

## Target

- Phone: Samsung Galaxy S26 Ultra
- Model: samsung SM-S948U1
- SoC: QTI SM8850
- Android: 16 / SDK 36
- ABIs: arm64-v8a

## Execution Units

### cpu.arm64.app_process

- Kind: cpu
- Status: reachable
- Access: android_app_process
- Confidence: high
- Execution model: shared_memory_os_threads
- Evidence: /proc/cpuinfo readable; Runtime.availableProcessors

### gpu.adreno.hints

- Kind: gpu
- Status: hints_detected
- Access: library_listing_only
- Confidence: medium
- Execution model: unknown_gpu_runtime
- Evidence: Android library listings; getprop ro.hardware.egl when available

### accelerator.cdsp_htp_qnn.hints

- Kind: npu_or_dsp_hint
- Status: hints_detected
- Access: library_listing_only
- Confidence: medium
- Execution model: unknown_dsp_or_npu_runtime
- Evidence: Android library listings; thermal/cooling CDSP hints if present

### thermal.cooling_control

- Kind: thermal
- Status: hints_detected
- Access: sysfs_read_only
- Confidence: high
- Execution model: telemetry_and_throttling_context
- Evidence: /sys/class/thermal readable

## Probe Gaps

- No JNI/NDK instruction probes have run yet.
- No native kernel correctness tests have run on Android yet.
- Vulkan availability requires real API enumeration; library hints were insufficient.
- QNN availability requires direct library load/API probing; first probe did not prove libQnn availability.
- No accelerator execution or performance benchmark has run.

## Next Gates

- android_native_smoke_jni
- cpu_isa_feature_probe
- native_kernel_correctness_microfixtures
- native_cpu_microbench_json
- backend_runtime_load_probe

## Structured Fuzzing Plan

### cpu_arm64_isa_feature_probe

- Purpose: Validate reported CPU feature flags with tiny guarded native instructions.
- Requires: Android NDK/JNI
- Safety: Run one candidate per guarded probe using SIGILL handling or process isolation.
- Output: feature_name, compiled, executed, sigill_or_ok, latency_ns_optional

### thread_topology_probe

- Purpose: Map CPU thread scaling and infer big/mid/little behavior from latency and affinity when allowed.
- Requires: Android NDK/JNI
- Safety: Use short bounded loops and record thermal state.
- Output: threads, latency, throughput, thermal_snapshot

### memory_hierarchy_probe

- Purpose: Measure app-visible memory bandwidth and latency regimes for kernel tiling decisions.
- Requires: Android NDK/JNI
- Safety: Use small buffers first; cap allocation sizes well below available memory.
- Output: buffer_bytes, stride, bandwidth_gbps, latency_ns

### backend_runtime_load_probe

- Purpose: Check whether Vulkan, NNAPI, QNN, or SNPE-like libraries can be loaded and minimally enumerated.
- Requires: Android Java APIs plus optional NDK dlopen
- Safety: Load and unload libraries only; do not execute untrusted accelerator kernels.
- Output: backend, library, load_status, api_version_or_error

### native_kernel_correctness_probe

- Purpose: Run tiny deterministic matvec, int4 dequant, RMSNorm, RoPE, and softmax kernels against references.
- Requires: Android NDK/JNI
- Safety: Tiny tensors only; no model weights.
- Output: operator, shape, max_abs_error, passed

