#include "backends/nnapi/nnapi_backend.h"

namespace qpnpu {

const char* NnapiBackend::name() const {
    return "nnapi";
}

bool NnapiBackend::is_available() const {
    return false;
}

const char* NnapiBackend::unavailable_reason() const {
    return "Phase 2 has no Android native/app integration, so NNAPI execution is unavailable.";
}

}  // namespace qpnpu