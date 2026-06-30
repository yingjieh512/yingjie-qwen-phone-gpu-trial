# Android

Android artifacts live under this directory.

- `probe-app/`: minimal Java-only QPNPU Probe APK for Phase 4A AWS Device Farm Remote Access smoke validation.

The Phase 4A APK collects best-effort hardware information, displays JSON on screen, logs it to logcat, and tries to save `probe_result.json` in app-private external files. It does not run Qwen inference, QNN, NPU kernels, or benchmarks.