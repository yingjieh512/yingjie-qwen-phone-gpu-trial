#include "qpnpu/kernels.h"

#include <cmath>

namespace qpnpu {

void rmsnorm_ref(
    const float* x,
    const float* weight,
    float* output,
    std::size_t n,
    float eps) {
    if (n == 0) {
        return;
    }

    double sum_squares = 0.0;
    for (std::size_t i = 0; i < n; ++i) {
        sum_squares += static_cast<double>(x[i]) * static_cast<double>(x[i]);
    }
    const double mean_square = sum_squares / static_cast<double>(n);
    const float inv_rms = static_cast<float>(1.0 / std::sqrt(mean_square + static_cast<double>(eps)));
    for (std::size_t i = 0; i < n; ++i) {
        output[i] = x[i] * inv_rms * weight[i];
    }
}

}  // namespace qpnpu