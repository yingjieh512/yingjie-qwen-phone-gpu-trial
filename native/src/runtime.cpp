#include "qpnpu/backend.h"

namespace qpnpu {

std::vector<BackendInfo> phase2_backend_infos() {
    return {
        {"cpu", true, ""},
        {"vulkan", false, "Phase 2 provides a Vulkan stub only; no Vulkan execution is implemented."},
        {"nnapi", false, "Phase 2 requires a later Android native/app phase for NNAPI execution."},
        {"qnn", false, "Phase 2 has not integrated the Qualcomm QNN SDK or runtime."},
    };
}

}  // namespace qpnpu