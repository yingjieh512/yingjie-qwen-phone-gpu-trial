#include "qpnpu/kernels.h"

#include <cassert>
#include <cmath>
#include <vector>

int main() {
    const std::vector<float> logits = {1000.0f, 1001.0f, 1002.0f};
    std::vector<float> output(logits.size(), 0.0f);
    qpnpu::softmax_ref(logits.data(), output.data(), logits.size());

    float sum = 0.0f;
    for (float value : output) {
        assert(std::isfinite(value));
        assert(value > 0.0f);
        sum += value;
    }
    assert(std::fabs(sum - 1.0f) < 1e-5f);
    assert(output[0] < output[1]);
    assert(output[1] < output[2]);
    return 0;
}