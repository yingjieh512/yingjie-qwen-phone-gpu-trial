#pragma once

namespace qpnpu {

struct ProbeBackendAvailability {
    bool cpu;
    bool vulkan;
    bool nnapi;
    bool qnn;
};

}  // namespace qpnpu

