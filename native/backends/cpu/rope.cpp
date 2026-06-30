#include "qpnpu/kernels.h"

#include <cmath>

namespace qpnpu {

void rope_ref(
    const float* x,
    float* output,
    std::size_t n,
    std::size_t position,
    float theta_base) {
    if (theta_base <= 0.0f) {
        theta_base = 10000.0f;
    }

    for (std::size_t i = 0; i + 1 < n; i += 2) {
        const std::size_t pair_index = i / 2;
        const double exponent = static_cast<double>(2 * pair_index) / static_cast<double>(n);
        const double inv_freq = std::pow(static_cast<double>(theta_base), -exponent);
        const double angle = static_cast<double>(position) * inv_freq;
        const float c = static_cast<float>(std::cos(angle));
        const float s = static_cast<float>(std::sin(angle));
        const float even = x[i];
        const float odd = x[i + 1];
        output[i] = even * c - odd * s;
        output[i + 1] = even * s + odd * c;
    }

    if (n % 2 != 0) {
        output[n - 1] = x[n - 1];
    }
}

}  // namespace qpnpu