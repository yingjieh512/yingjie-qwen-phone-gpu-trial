#pragma once

#include "qpnpu/backend.h"

namespace qpnpu {

class QnnBackend final : public Backend {
public:
    const char* name() const override;
    bool is_available() const override;
    const char* unavailable_reason() const override;
};

}  // namespace qpnpu