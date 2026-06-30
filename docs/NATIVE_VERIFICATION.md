# Native Verification

Phase 2 native verification proves that the local C++17 foundation builds, CPU reference kernels pass correctness tests, and the local CPU microbenchmark can emit benchmark-schema JSON.

It does not prove Android, phone, QNN, Vulkan, NNAPI, or NPU performance.

## Quick Check

Run:

```bash
python scripts/dev/verify_phase2.py
```

If local native tools are missing, the script prints `BLOCKED` for native verification instead of treating missing CMake or a compiler as a source failure.

Python-only verification:

```bash
python scripts/dev/verify_phase2.py --skip-native
```

## Windows Setup

Install:

- CMake
- Visual Studio Build Tools
- Desktop development with C++ workload

Then open a Developer PowerShell or Developer Command Prompt and run:

```powershell
python scripts/dev/verify_phase2.py --config Release
```

For Visual Studio generators, native executables may be under:

- `native/build/Debug/qpnpu_microbench.exe`
- `native/build/Release/qpnpu_microbench.exe`

The Python wrapper searches those paths automatically.

## Linux/macOS Setup

Linux:

```bash
sudo apt-get update
sudo apt-get install -y cmake build-essential
python scripts/dev/verify_phase2.py
```

macOS:

```bash
xcode-select --install
brew install cmake
python scripts/dev/verify_phase2.py
```

Use equivalent package-manager commands if your system differs.

## Manual Native Commands

```bash
cmake -S native -B native/build
cmake --build native/build --config Release
ctest --test-dir native/build --build-config Release --output-on-failure
python scripts/native/run_local_microbench.py --build-dir native/build --out benchmarks/results/local_microbench.json
```

## GitHub Actions

The repository includes `.github/workflows/ci.yml`. CI runs on `ubuntu-latest` and validates:

- Python dependency installation
- `python -m pytest tests`
- native CMake configure/build
- native CTest
- native microbench smoke
- Python microbench wrapper

After pushing a branch, open the repository's Actions tab and inspect the `CI` workflow.

## Interpreting Blocked Native Verification

`Phase 2 code implemented but native verification blocked` means the repository has native source and tests, but the current machine lacks required local tools such as CMake, CTest, or a C++ compiler.

That is different from a native test failure. A real failure means CMake, build, CTest, or microbench execution ran and returned nonzero.

## Performance Note

The local CPU microbenchmark is not a phone benchmark and not an NPU benchmark. Its JSON contains a warning:

```text
local CPU microbenchmark; not a phone or NPU performance claim
```

Do not compare local desktop CPU operator timings to the long-term Android phone decode target.

