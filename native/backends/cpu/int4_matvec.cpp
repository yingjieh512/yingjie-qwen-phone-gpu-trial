#include "qpnpu/kernels.h"

#include <cstdint>

namespace qpnpu {
namespace {

int decode_signed_int4(std::uint8_t nibble) {
    const int value = static_cast<int>(nibble & 0x0F);
    return value >= 8 ? value - 16 : value;
}

}  // namespace

void fp32_matvec_ref(
    const float* matrix,
    const float* vector,
    float* output,
    std::size_t rows,
    std::size_t cols) {
    for (std::size_t row = 0; row < rows; ++row) {
        float acc = 0.0f;
        for (std::size_t col = 0; col < cols; ++col) {
            acc += matrix[row * cols + col] * vector[col];
        }
        output[row] = acc;
    }
}

void int4_groupwise_matvec_ref(
    const std::uint8_t* packed_weights,
    const float* scales,
    const float* vector,
    float* output,
    std::size_t rows,
    std::size_t cols,
    std::size_t group_size) {
    if (group_size == 0) {
        for (std::size_t row = 0; row < rows; ++row) {
            output[row] = 0.0f;
        }
        return;
    }

    const std::size_t groups_per_row = (cols + group_size - 1) / group_size;
    for (std::size_t row = 0; row < rows; ++row) {
        float acc = 0.0f;
        for (std::size_t col = 0; col < cols; ++col) {
            const std::size_t linear = row * cols + col;
            const std::uint8_t byte = packed_weights[linear / 2];
            const std::uint8_t nibble = (linear % 2 == 0) ? (byte & 0x0F) : ((byte >> 4) & 0x0F);
            const int quantized = decode_signed_int4(nibble);
            const std::size_t group = col / group_size;
            const float scale = scales[row * groups_per_row + group];
            acc += static_cast<float>(quantized) * scale * vector[col];
        }
        output[row] = acc;
    }
}

}  // namespace qpnpu