#include "qpnpu/kernels.h"

#include <cassert>
#include <cmath>
#include <vector>

namespace {

bool close(float a, float b, float tol = 1e-5f) {
    return std::fabs(a - b) <= tol;
}

float pair_norm(float a, float b) {
    return std::sqrt(a * a + b * b);
}

}  // namespace

int main() {
    const std::vector<float> x = {1.0f, 2.0f, 3.0f, 4.0f};
    std::vector<float> output(x.size(), 0.0f);

    qpnpu::rope_ref(x.data(), output.data(), x.size(), 0, 10000.0f);
    for (std::size_t i = 0; i < x.size(); ++i) {
        assert(close(output[i], x[i]));
    }

    qpnpu::rope_ref(x.data(), output.data(), x.size(), 7, 10000.0f);
    for (float value : output) {
        assert(std::isfinite(value));
    }
    assert(close(pair_norm(output[0], output[1]), pair_norm(x[0], x[1]), 1e-4f));
    assert(close(pair_norm(output[2], output[3]), pair_norm(x[2], x[3]), 1e-4f));
    return 0;
}