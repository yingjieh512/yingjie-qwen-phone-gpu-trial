#pragma once

#include "qpnpu/backend.h"

namespace qpnpu {

class CpuBackend final : public Backend {
public:
    const char* name() const override;
    bool is_available() const override;
    const char* unavailable_reason() const override;

    bool run_fp32_matvec(
        const float* matrix,
        const float* vector,
        float* output,
        std::size_t rows,
        std::size_t cols) override;

    bool run_rmsnorm(
        const float* x,
        const float* weight,
        float* output,
        std::size_t n,
        float eps) override;

    bool run_rope(
        const float* x,
        float* output,
        std::size_t n,
        std::size_t position,
        float theta_base) override;

    bool run_int4_matvec(
        const std::uint8_t* packed_weights,
        const float* scales,
        const float* vector,
        float* output,
        std::size_t rows,
        std::size_t cols,
        std::size_t group_size) override;
};

}  // namespace qpnpu