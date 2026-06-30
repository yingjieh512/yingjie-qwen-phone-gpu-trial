#pragma once

namespace qpnpu {

struct ProbeBackendAvailability {
    bool cpu;
    bool vulkan;
    bool nnapi;
    bool qnn;
};

ProbeBackendAvailability phase2_probe_backend_availability();

}  // namespace qpnpu