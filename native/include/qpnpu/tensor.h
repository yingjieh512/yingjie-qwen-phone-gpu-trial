#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

namespace qpnpu {

enum class DType {
    FP32,
    FP16,
    INT8,
    UINT8,
    INT4_PACKED,
};

const char* dtype_name(DType dtype);
std::size_t dtype_size_bytes(DType dtype);

struct TensorView {
    DType dtype{DType::FP32};
    std::vector<std::size_t> shape;
    void* data{nullptr};

    TensorView() = default;
    TensorView(DType dtype_value, std::vector<std::size_t> shape_value, void* data_value);

    std::size_t element_count() const;
    std::size_t byte_size() const;

    template <typename T>
    T* data_as() {
        return static_cast<T*>(data);
    }

    template <typename T>
    const T* data_as() const {
        return static_cast<const T*>(data);
    }
};

}  // namespace qpnpu