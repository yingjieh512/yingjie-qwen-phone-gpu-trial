#include "qpnpu/probe.h"

namespace qpnpu {

ProbeBackendAvailability phase2_probe_backend_availability() {
    return ProbeBackendAvailability{true, false, false, false};
}

}  // namespace qpnpu