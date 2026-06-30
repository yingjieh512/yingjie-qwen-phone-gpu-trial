#include "qpnpu/tensor.h"

#include <numeric>
#include <utility>

namespace qpnpu {

const char* dtype_name(DType dtype) {
    switch (dtype) {
        case DType::FP32:
            return "fp32";
        case DType::FP16:
            return "fp16";
        case DType::INT8:
            return "int8";
        case DType::UINT8:
            return "uint8";
        case DType::INT4_PACKED:
            return "int4_packed";
    }
    return "unknown";
}

std::size_t dtype_size_bytes(DType dtype) {
    switch (dtype) {
        case DType::FP32:
            return 4;
        case DType::FP16:
            return 2;
        case DType::INT8:
        case DType::UINT8:
            return 1;
        case DType::INT4_PACKED:
            return 0;
    }
    return 0;
}

TensorView::TensorView(DType dtype_value, std::vector<std::size_t> shape_value, void* data_value)
    : dtype(dtype_value), shape(std::move(shape_value)), data(data_value) {}

std::size_t TensorView::element_count() const {
    if (shape.empty()) {
        return 0;
    }
    return std::accumulate(shape.begin(), shape.end(), static_cast<std::size_t>(1),
                           [](std::size_t a, std::size_t b) { return a * b; });
}

std::size_t TensorView::byte_size() const {
    const std::size_t elements = element_count();
    if (dtype == DType::INT4_PACKED) {
        return (elements + 1) / 2;
    }
    return elements * dtype_size_bytes(dtype);
}

}  // namespace qpnpu