#pragma once

#include <cstddef>

namespace qpnpu {

int int4_matvec_placeholder(const void* weights, const void* input, void* output, std::size_t elements);

}  // namespace qpnpu

