#pragma once

namespace qpnpu {

struct ModelMetadata {
    const char* architecture{"unknown"};
    const char* format{"qpnpu"};
};

bool is_qpnpu_format(const ModelMetadata& metadata);

}  // namespace qpnpu