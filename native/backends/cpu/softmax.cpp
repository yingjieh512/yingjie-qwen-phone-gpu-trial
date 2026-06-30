#include "qpnpu/kernels.h"

#include <algorithm>
#include <cmath>

namespace qpnpu {

void softmax_ref(
    const float* logits,
    float* output,
    std::size_t n) {
    if (n == 0) {
        return;
    }

    const float max_value = *std::max_element(logits, logits + n);
    double sum = 0.0;
    for (std::size_t i = 0; i < n; ++i) {
        output[i] = static_cast<float>(std::exp(static_cast<double>(logits[i] - max_value)));
        sum += output[i];
    }

    if (sum == 0.0) {
        return;
    }
    const float inv_sum = static_cast<float>(1.0 / sum);
    for (std::size_t i = 0; i < n; ++i) {
        output[i] *= inv_sum;
    }
}

}  // namespace qpnpu