#include "backends/vulkan/vulkan_backend.h"

namespace qpnpu {

const char* VulkanBackend::name() const {
    return "vulkan";
}

bool VulkanBackend::is_available() const {
    return false;
}

const char* VulkanBackend::unavailable_reason() const {
    return "Phase 2 provides a Vulkan backend stub only; no Vulkan execution is implemented.";
}

}  // namespace qpnpu