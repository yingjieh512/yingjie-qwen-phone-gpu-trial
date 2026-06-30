#include "qpnpu/model.h"

#include <cstring>

namespace qpnpu {

bool is_qpnpu_format(const ModelMetadata& metadata) {
    return metadata.format != nullptr && std::strcmp(metadata.format, "qpnpu") == 0;
}

}  // namespace qpnpu