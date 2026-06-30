#include "qpnpu/kernels.h"

#include <cassert>
#include <cmath>
#include <vector>

namespace {

bool close(float a, float b, float tol = 1e-5f) {
    return std::fabs(a - b) <= tol;
}

}  // namespace

int main() {
    const std::vector<float> x = {1.0f, 2.0f, 3.0f};
    const std::vector<float> weight = {1.0f, 0.5f, 2.0f};
    std::vector<float> output(x.size(), 0.0f);
    qpnpu::rmsnorm_ref(x.data(), weight.data(), output.data(), x.size(), 1e-5f);

    const float mean_square = (1.0f + 4.0f + 9.0f) / 3.0f;
    const float inv_rms = 1.0f / std::sqrt(mean_square + 1e-5f);
    assert(close(output[0], x[0] * inv_rms * weight[0]));
    assert(close(output[1], x[1] * inv_rms * weight[1]));
    assert(close(output[2], x[2] * inv_rms * weight[2]));
    return 0;
}