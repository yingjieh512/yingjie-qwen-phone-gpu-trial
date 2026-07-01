# Target Hardware Profile

Generated from Android probe source `android-probe-app` at `2026-07-01T00:33:01Z`.

## Device

- Manufacturer: samsung
- Model: SM-S948U1
- Device: m3q
- Board: canoe
- Hardware: qcom
- SoC: QTI SM8850
- Android: 16 / SDK 36
- ABIs: arm64-v8a

## CPU And Memory

- Available processors: 8
- CPU info readable: True
- Feature flags present: asimddp, i8mm, bf16, sve, sve2, svei8mm, sme, sha3
- MemTotal: 11389632 kB
- MemAvailable: 5698916 kB
- Runtime max memory: 268435456 bytes

## GPU Hints

- Status: hints_detected
- Vulkan libraries detected: False
- Hint count: 18
- Notable hints: /vendor/lib64/libEGL_adreno.so, /vendor/lib64/libGLESv2_adreno.so, /vendor/lib64/libOpenCL.so, /vendor/lib64/libOpenCL_adreno.so, /vendor/lib64/libadreno_app_profiles.so, /vendor/lib64/libadreno_compiler_cl.so, /vendor/lib64/libadreno_utils.so, /system/lib64/libAdrenoQProfiler.so, /system/lib64/libGLESv1_CM.so, /system/lib64/libGLESv1_CM_angle.so, /system/lib64/libGLESv2.so, /system/lib64/libGLESv2_angle.so, /system/lib64/libGLESv3.so, /system/lib64/libaivp_opencl.so, /system_ext/lib64/libOpenCL_system.so
- Availability claim: none

## NPU/DSP Hints

- Status: hints_detected
- QNN libraries detected: False
- NNAPI string hints detected: False
- Hint count: 6
- Notable hints: /vendor/lib64/cdsp_face.so, /vendor/lib64/libSnpeHtpV81Stub.so, /vendor/lib64/libadsp_default_listener.so, /vendor/lib64/libadsprpc.so, /vendor/lib64/libcdsp_default_listener.so, /vendor/lib64/libcdsprpc.so
- Availability claim: none; string hints are not proof of NPU availability

## Thermal

- Status: hints_detected
- Zone count: 64
- Notable zones: cpufreq-cpu0, cpufreq-cpu6, cpu-hotplug7, pause-cpu0, pause-cpu1, pause-cpu2, pause-cpu3, ufs, pause-cpu4, pause-cpu5, pause-cpu6, pause-cpu7, cpu-hotplug0, cpu-cluster0, cpu-cluster1, ddr-cdev, cdsp_ss, cdsp_hw, kgsl, cdsp, gpu, cpu-hotplug1, cdsp_sw_hvx, cdsp_sw_hmx

## Interpretation

- CPU fallback should be treated as mandatory; the probe confirms app-side execution and readable CPU/memory data.
- NPU/DSP string hints were detected, but no QNN library availability was proven by this probe.
- GPU/OpenCL/GLES hints were detected, but Vulkan was not proven by this probe.
- Thermal/cooling entries were readable, so future benchmark JSON should capture thermal state.

This profile is hardware discovery evidence only. It is not a performance result and does not prove QNN, NPU, Vulkan, or NNAPI execution.
