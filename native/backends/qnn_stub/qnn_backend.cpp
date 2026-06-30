#include "backends/qnn_stub/qnn_backend.h"

namespace qpnpu {

const char* QnnBackend::name() const {
    return "qnn";
}

bool QnnBackend::is_available() const {
    return false;
}

const char* QnnBackend::unavailable_reason() const {
    return "Phase 2 has not integrated the Qualcomm QNN SDK or runtime; QNN execution is unavailable.";
}

}  // namespace qpnpu