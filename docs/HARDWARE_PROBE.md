# Hardware Probe

The future Android hardware probe will detect actual device capabilities at runtime. It must not assume that a Samsung Galaxy S26 Ultra-class phone exposes any particular NPU backend.

Planned probe fields:

- `device`: manufacturer, model, Android version, SoC hints, ABI list.
- `cpu`: core topology, supported instruction features, max frequency hints.
- `memory`: total memory, available memory, memory bandwidth microbenchmarks when available.
- `gpu`: renderer, driver, Vulkan availability, compute feature hints.
- `npu`: NNAPI availability, QNN availability, vendor libraries, accelerator names when exposed.
- `thermal`: thermal zones, throttling state, battery state.
- `microbenchmarks`: tiny operator timings used only for backend and kernel planning.
- `warnings`: conservative notes about missing permissions, missing tools, or sample data.

Phase 0 status:

- Only a JSON schema helper and sample probe are provided.
- No Android APK exists.
- No hardware detection is implemented.
- No NPU support is claimed.

