#include "backends/cpu/cpu_backend.h"

#include "qpnpu/kernels.h"

namespace qpnpu {

const char* CpuBackend::name() const {
    return "cpu";
}

bool CpuBackend::is_available() const {
    return true;
}

const char* CpuBackend::unavailable_reason() const {
    return "";
}

bool CpuBackend::run_fp32_matvec(
    const float* matrix,
    const float* vector,
    float* output,
    std::size_t rows,
    std::size_t cols) {
    fp32_matvec_ref(matrix, vector, output, rows, cols);
    return true;
}

bool CpuBackend::run_rmsnorm(
    const float* x,
    const float* weight,
    float* output,
    std::size_t n,
    float eps) {
    rmsnorm_ref(x, weight, output, n, eps);
    return true;
}

bool CpuBackend::run_rope(
    const float* x,
    float* output,
    std::size_t n,
    std::size_t position,
    float theta_base) {
    rope_ref(x, output, n, position, theta_base);
    return true;
}

bool CpuBackend::run_int4_matvec(
    const std::uint8_t* packed_weights,
    const float* scales,
    const float* vector,
    float* output,
    std::size_t rows,
    std::size_t cols,
    std::size_t group_size) {
    int4_groupwise_matvec_ref(packed_weights, scales, vector, output, rows, cols, group_size);
    return true;
}

}  // namespace qpnpu