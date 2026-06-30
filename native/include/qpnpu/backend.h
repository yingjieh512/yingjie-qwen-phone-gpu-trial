#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

namespace qpnpu {

enum class BackendKind {
    Cpu,
    Vulkan,
    Nnapi,
    Qnn,
};

struct BackendInfo {
    const char* name;
    bool available;
    const char* unavailable_reason;
};

class Backend {
public:
    virtual ~Backend() = default;

    virtual const char* name() const = 0;
    virtual bool is_available() const = 0;
    virtual const char* unavailable_reason() const = 0;

    virtual bool run_fp32_matvec(
        const float*, const float*, float*, std::size_t, std::size_t) {
        return false;
    }

    virtual bool run_rmsnorm(
        const float*, const float*, float*, std::size_t, float) {
        return false;
    }

    virtual bool run_rope(
        const float*, float*, std::size_t, std::size_t, float) {
        return false;
    }

    virtual bool run_int4_matvec(
        const std::uint8_t*, const float*, const float*, float*, std::size_t, std::size_t, std::size_t) {
        return false;
    }
};

std::vector<BackendInfo> phase2_backend_infos();

}  // namespace qpnpu