# Hardware Characterization Ladder

The job-description target is not a static hardware inventory. It is a strict ladder that turns partial hardware evidence into a behavioral model, then uses that model to choose compiler, kernel, runtime, and inference-stack decisions.

This repository now treats the Android probe as the first rung of that ladder.

## Rung 1: App-Reachable Evidence

Implemented in Phase 4A/4B.

- Android build/device fields.
- Selected `getprop` fields.
- `/proc/cpuinfo` and `/proc/meminfo` excerpts.
- App-readable library listings.
- GPU/NPU/DSP string hints.
- Thermal/cooling sysfs hints.
- Logcat JSON extraction.
- Execution-model-neutral hardware model generation.

Output:

- `benchmarks/results/aws_remote_probe_2026-07-01.json`
- `benchmarks/results/aws_remote_probe_2026-07-01.summary.json`
- `benchmarks/results/aws_remote_probe_2026-07-01.hw_model.json`
- `docs/TARGET_HARDWARE_PROFILE.md`
- `docs/HARDWARE_CHARACTERIZATION.md`

Limit:

- This rung does not execute native instructions or accelerator kernels.

## Rung 2: Native Android Smoke

Next phase.

- Add JNI/NDK.
- Load one tiny native library from the APK.
- Return native build info, ABI, page size, timer availability, and CPU count.
- Emit JSON through the same UI/logcat path.

Gate:

- Java can call native code.
- Native code can return structured JSON.
- App remains stable on Device Farm.

## Rung 3: Structured CPU ISA Probes

Use tiny guarded native probes to validate feature flags instead of trusting `/proc/cpuinfo`.

Candidate probes:

- NEON/ASIMD baseline.
- dot product / `asimddp`.
- i8mm / `svei8mm` where the compiler supports it.
- BF16.
- SVE/SVE2 presence and vector-length query.
- SME presence only through safe feature detection or guarded probes.

Safety rule:

- Each candidate must be isolated behind compile-time guards and runtime signal handling or process isolation. A bad instruction must become a failed probe result, not an app crash.

Output:

- `feature_name`
- `reported_by_cpuinfo`
- `compiled`
- `executed`
- `sigill_or_ok`
- `notes`

## Rung 4: Memory And Thread Topology

Measure behavior that affects tiling decisions.

- Thread scaling.
- Approximate big/mid/little cluster behavior.
- Memory bandwidth by buffer size.
- Stride sensitivity.
- Thermal state before/after short workloads.

Output:

- latency/throughput by thread count
- bandwidth by size/stride
- thermal snapshot

## Rung 5: Backend Runtime Loading

Move from string hints to real runtime availability checks.

- NNAPI Java enumeration.
- Vulkan API instance/device enumeration if available.
- NDK `dlopen` checks for QNN/SNPE-like libraries.
- Symbol lookup only; no accelerator execution yet.

Gate:

- Runtime library/API is actually reachable from app context.

## Rung 6: Native Kernel Correctness

Run tiny deterministic kernels against references.

- fp32 matvec.
- int4 dequant matvec.
- RMSNorm.
- RoPE.
- softmax.

Gate:

- Correctness passes before timing matters.

## Rung 7: Native Microbenchmarks

Only after correctness.

- Emit benchmark-schema JSON.
- Include thermal context.
- Keep tensors tiny and deterministic.
- Do not compare to Qwen 9B target.

## Rung 8: Generated Kernel Search

Use the hardware model and microbench data to generate candidate kernels.

- Tile-size candidates.
- Vectorization candidates.
- Thread partitioning candidates.
- Memory layout candidates.

Gate:

- Generated kernel correctness before speed selection.

## Rung 9: Small Model Runtime

Package tiny model fixtures into the APK and run end-to-end decode.

Gate:

- Model-format loading, tensor loading, decode loop, and benchmark JSON all work on Android.

## Rung 10: Full Model Strategy

Only after the Android runtime is stable.

- Decide how Qwen 9B weights are quantized, sharded, transferred, loaded, and validated.
- Device Farm may validate APK behavior, but full-model iteration likely needs a local phone with ADB because multi-GB model logistics are awkward in Remote Access.

## Principle

Every rung must emit structured JSON, be reproducible, and feed the next rung. String hints never become capability claims until an executable probe proves them.
