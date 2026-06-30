#pragma once

namespace qpnpu {

enum class BackendKind {
    Cpu,
    Vulkan,
    Nnapi,
    Qnn,
};

struct BackendInfo {
    BackendKind kind;
    bool available;
};

}  // namespace qpnpu

