#include "backends/cpu/cpu_backend.h"
#include "backends/nnapi/nnapi_backend.h"
#include "backends/qnn_stub/qnn_backend.h"
#include "backends/vulkan/vulkan_backend.h"
#include "qpnpu/backend.h"
#include "qpnpu/probe.h"

#include <cassert>
#include <cstring>

int main() {
    qpnpu::CpuBackend cpu;
    qpnpu::VulkanBackend vulkan;
    qpnpu::NnapiBackend nnapi;
    qpnpu::QnnBackend qnn;

    assert(std::strcmp(cpu.name(), "cpu") == 0);
    assert(cpu.is_available());

    assert(!vulkan.is_available());
    assert(std::strlen(vulkan.unavailable_reason()) > 0);
    assert(!nnapi.is_available());
    assert(std::strlen(nnapi.unavailable_reason()) > 0);
    assert(!qnn.is_available());
    assert(std::strlen(qnn.unavailable_reason()) > 0);

    const auto infos = qpnpu::phase2_backend_infos();
    assert(infos.size() == 4);
    assert(infos[0].available);

    const auto availability = qpnpu::phase2_probe_backend_availability();
    assert(availability.cpu);
    assert(!availability.vulkan);
    assert(!availability.nnapi);
    assert(!availability.qnn);
    return 0;
}