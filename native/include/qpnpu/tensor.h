#pragma once

#include <cstddef>

namespace qpnpu {

struct TensorShape {
    const std::size_t* dims;
    std::size_t rank;
};

}  // namespace qpnpu

