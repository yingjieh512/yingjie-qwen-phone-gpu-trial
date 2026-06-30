#pragma once

#include <cstddef>
#include <cstdint>

namespace qpnpu {

void fp32_matvec_ref(
    const float* matrix,
    const float* vector,
    float* output,
    std::size_t rows,
    std::size_t cols);

void int4_groupwise_matvec_ref(
    const std::uint8_t* packed_weights,
    const float* scales,
    const float* vector,
    float* output,
    std::size_t rows,
    std::size_t cols,
    std::size_t group_size);

void rmsnorm_ref(
    const float* x,
    const float* weight,
    float* output,
    std::size_t n,
    float eps);

void rope_ref(
    const float* x,
    float* output,
    std::size_t n,
    std::size_t position,
    float theta_base = 10000.0f);

void softmax_ref(
    const float* logits,
    float* output,
    std::size_t n);

}  // namespace qpnpu