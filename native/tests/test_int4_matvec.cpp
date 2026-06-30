#include "qpnpu/kernels.h"

#include <cassert>
#include <cmath>
#include <cstdint>
#include <vector>

namespace {

std::uint8_t encode_int4(int value) {
    assert(value >= -8 && value <= 7);
    return static_cast<std::uint8_t>(value) & 0x0F;
}

std::vector<std::uint8_t> pack_int4(const std::vector<int>& values) {
    std::vector<std::uint8_t> packed((values.size() + 1) / 2, 0);
    for (std::size_t i = 0; i < values.size(); ++i) {
        const std::uint8_t nibble = encode_int4(values[i]);
        if (i % 2 == 0) {
            packed[i / 2] |= nibble;
        } else {
            packed[i / 2] |= static_cast<std::uint8_t>(nibble << 4);
        }
    }
    return packed;
}

bool close(float a, float b, float tol = 1e-5f) {
    return std::fabs(a - b) <= tol;
}

}  // namespace

int main() {
    const std::size_t rows = 2;
    const std::size_t cols = 5;
    const std::size_t group_size = 3;
    const std::vector<int> qweights = {
        1, -2, 3, 4, -1,
        -8, 7, 0, 2, -3,
    };
    const std::vector<std::uint8_t> packed = pack_int4(qweights);
    const std::vector<float> scales = {
        0.5f, 2.0f,
        0.25f, 1.0f,
    };
    const std::vector<float> vector = {1.0f, 2.0f, -1.0f, 0.5f, 3.0f};
    std::vector<float> output(rows, 0.0f);

    qpnpu::int4_groupwise_matvec_ref(
        packed.data(), scales.data(), vector.data(), output.data(), rows, cols, group_size);

    assert(close(output[0], -5.0f));
    assert(close(output[1], -6.5f));
    return 0;
}