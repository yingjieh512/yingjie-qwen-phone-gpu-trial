#include <jni.h>

#include <algorithm>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <dlfcn.h>
#include <fstream>
#include <iomanip>
#include <sched.h>
#include <sstream>
#include <string>
#include <thread>
#include <unistd.h>
#include <vector>

#if defined(__ANDROID__) && defined(__aarch64__)
#include <asm/hwcap.h>
#include <sys/auxv.h>
#endif

#ifndef AT_HWCAP
#define AT_HWCAP 16
#endif

#ifndef AT_HWCAP2
#define AT_HWCAP2 26
#endif

namespace {

constexpr const char* kBackend = "cpu_android_native_reference";

volatile uint64_t g_phase6_sink = 0;

std::string JsonEscape(const std::string& value) {
    std::ostringstream out;
    for (char ch : value) {
        switch (ch) {
            case '\\': out << "\\\\"; break;
            case '"': out << "\\\""; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default:
                if (static_cast<unsigned char>(ch) < 0x20) {
                    out << "\\u" << std::hex << std::setw(4) << std::setfill('0')
                        << static_cast<int>(static_cast<unsigned char>(ch));
                } else {
                    out << ch;
                }
        }
    }
    return out.str();
}

std::string JsonBool(bool value) {
    return value ? "true" : "false";
}

std::string ReadSmallTextFile(const std::string& path, size_t max_bytes) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        return "";
    }
    std::string text(max_bytes, '\0');
    input.read(&text[0], static_cast<std::streamsize>(max_bytes));
    text.resize(static_cast<size_t>(input.gcount()));
    return text;
}

bool TextContainsToken(const std::string& text, const std::string& token) {
    return text.find(token) != std::string::npos;
}

uint64_t SafeGetAuxv(unsigned long key) {
#if defined(__ANDROID__) && defined(__aarch64__)
    errno = 0;
    return static_cast<uint64_t>(getauxval(key));
#else
    (void)key;
    return 0;
#endif
}

std::string CpuFeatureJson(const std::string& name,
                           const std::string& cpuinfo_token,
                           bool cpuinfo_reported,
                           bool auxv_macro_available,
                           bool auxv_reported,
                           const std::string& auxv_register) {
    std::string status;
    if (cpuinfo_reported && auxv_reported) {
        status = "reported_by_cpuinfo_and_auxv";
    } else if (cpuinfo_reported) {
        status = auxv_macro_available ? "reported_by_cpuinfo_only" : "reported_by_cpuinfo_auxv_macro_unavailable";
    } else if (auxv_reported) {
        status = "reported_by_auxv_only";
    } else {
        status = "not_reported";
    }

    std::ostringstream out;
    out << "{";
    out << "\"name\":\"" << JsonEscape(name) << "\",";
    out << "\"cpuinfo_token\":\"" << JsonEscape(cpuinfo_token) << "\",";
    out << "\"cpuinfo_reported\":" << JsonBool(cpuinfo_reported) << ",";
    out << "\"auxv_macro_available\":" << JsonBool(auxv_macro_available) << ",";
    out << "\"auxv_reported\":" << JsonBool(auxv_reported) << ",";
    out << "\"auxv_register\":\"" << JsonEscape(auxv_register) << "\",";
    out << "\"status\":\"" << JsonEscape(status) << "\"";
    out << "}";
    return out.str();
}

std::string CpuIsaJson() {
    const std::string cpuinfo = ReadSmallTextFile("/proc/cpuinfo", 65536);
    const uint64_t hwcap = SafeGetAuxv(AT_HWCAP);
    const uint64_t hwcap2 = SafeGetAuxv(AT_HWCAP2);

    struct FeatureSpec {
        const char* name;
        const char* token;
        const char* reg;
        uint64_t mask;
        bool macro_available;
    };

    const std::vector<FeatureSpec> features = {
#ifdef HWCAP_ASIMD
        {"asimd", "asimd", "AT_HWCAP", static_cast<uint64_t>(HWCAP_ASIMD), true},
#else
        {"asimd", "asimd", "AT_HWCAP", 0, false},
#endif
#ifdef HWCAP_ASIMDDP
        {"asimddp", "asimddp", "AT_HWCAP", static_cast<uint64_t>(HWCAP_ASIMDDP), true},
#else
        {"asimddp", "asimddp", "AT_HWCAP", 0, false},
#endif
#ifdef HWCAP_SVE
        {"sve", "sve", "AT_HWCAP", static_cast<uint64_t>(HWCAP_SVE), true},
#else
        {"sve", "sve", "AT_HWCAP", 0, false},
#endif
#ifdef HWCAP2_I8MM
        {"i8mm", "i8mm", "AT_HWCAP2", static_cast<uint64_t>(HWCAP2_I8MM), true},
#else
        {"i8mm", "i8mm", "AT_HWCAP2", 0, false},
#endif
#ifdef HWCAP2_BF16
        {"bf16", "bf16", "AT_HWCAP2", static_cast<uint64_t>(HWCAP2_BF16), true},
#else
        {"bf16", "bf16", "AT_HWCAP2", 0, false},
#endif
#ifdef HWCAP2_SVE2
        {"sve2", "sve2", "AT_HWCAP2", static_cast<uint64_t>(HWCAP2_SVE2), true},
#else
        {"sve2", "sve2", "AT_HWCAP2", 0, false},
#endif
#ifdef HWCAP2_SVEI8MM
        {"svei8mm", "svei8mm", "AT_HWCAP2", static_cast<uint64_t>(HWCAP2_SVEI8MM), true},
#else
        {"svei8mm", "svei8mm", "AT_HWCAP2", 0, false},
#endif
#ifdef HWCAP2_SME
        {"sme", "sme", "AT_HWCAP2", static_cast<uint64_t>(HWCAP2_SME), true},
#else
        {"sme", "sme", "AT_HWCAP2", 0, false},
#endif
#ifdef HWCAP_SHA3
        {"sha3", "sha3", "AT_HWCAP", static_cast<uint64_t>(HWCAP_SHA3), true},
#else
        {"sha3", "sha3", "AT_HWCAP", 0, false},
#endif
    };

    uint64_t scalar_checksum = 0;
    for (uint64_t i = 0; i < 4096; ++i) {
        scalar_checksum = (scalar_checksum * 1315423911u) ^ (i + 0x9e3779b97f4a7c15ULL);
    }

    std::ostringstream out;
    out << "{";
    out << "\"page_size_bytes\":" << static_cast<long long>(sysconf(_SC_PAGESIZE)) << ",";
    out << "\"auxv\":{\"AT_HWCAP\":" << hwcap << ",\"AT_HWCAP2\":" << hwcap2 << "},";
    out << "\"proc_cpuinfo_readable\":" << JsonBool(!cpuinfo.empty()) << ",";
    out << "\"features\":[";
    for (size_t i = 0; i < features.size(); ++i) {
        const auto& feature = features[i];
        const bool cpuinfo_reported = TextContainsToken(cpuinfo, feature.token);
        const uint64_t reg_value = std::string(feature.reg) == "AT_HWCAP" ? hwcap : hwcap2;
        const bool auxv_reported = feature.macro_available && ((reg_value & feature.mask) != 0);
        if (i) out << ",";
        out << CpuFeatureJson(feature.name, feature.token, cpuinfo_reported, feature.macro_available,
                              auxv_reported, feature.reg);
    }
    out << "],";
    out << "\"execution_probes\":[";
    out << "{\"id\":\"scalar_integer_loop\",\"compiled\":true,\"executed\":true,\"status\":\"ok\",\"checksum\":" << scalar_checksum << "},";
    out << "{\"id\":\"feature_specific_instruction_fuzzing\",\"compiled\":false,\"executed\":false,\"status\":\"deferred_until_sigill_isolation\",";
    out << "\"reason\":\"Phase 6 records cpuinfo and auxv agreement first; destructive ISA trials need signal/process isolation.\"}";
    out << "],";
    out << "\"warnings\":[\"reported ISA flags are evidence, not a guarantee of generated-kernel correctness\"]";
    out << "}";
    return out.str();
}

void ThreadSpinWork(int iterations, int seed, uint64_t* output) {
    uint64_t x = static_cast<uint64_t>(seed) + 0x12345678ULL;
    for (int i = 0; i < iterations; ++i) {
        x ^= x << 7;
        x ^= x >> 9;
        x += static_cast<uint64_t>(i) * 17ULL + 3ULL;
    }
    *output = x;
}

std::string AffinityJson() {
    std::ostringstream out;
    out << "{";
#if defined(__linux__)
    cpu_set_t set;
    CPU_ZERO(&set);
    if (sched_getaffinity(0, sizeof(set), &set) == 0) {
        out << "\"readable\":true,\"cpus\":[";
        bool first = true;
        for (int cpu = 0; cpu < CPU_SETSIZE; ++cpu) {
            if (CPU_ISSET(cpu, &set)) {
                if (!first) out << ",";
                out << cpu;
                first = false;
            }
        }
        out << "]";
    } else {
        out << "\"readable\":false,\"error\":\"" << JsonEscape(std::strerror(errno)) << "\"";
    }
#else
    out << "\"readable\":false,\"error\":\"not linux\"";
#endif
    out << "}";
    return out.str();
}

std::string TopologyJson() {
    const unsigned int hw_threads = std::max(1u, std::thread::hardware_concurrency());
    const std::vector<int> thread_counts = {1, 2, 4, static_cast<int>(std::min(8u, hw_threads))};
    std::ostringstream out;
    out << "{";
    out << "\"std_thread_hardware_concurrency\":" << hw_threads << ",";
    out << "\"sched_affinity\":" << AffinityJson() << ",";
    out << "\"thread_scaling\":[";
    bool first_case = true;
    for (int thread_count : thread_counts) {
        if (thread_count <= 0 || static_cast<unsigned int>(thread_count) > hw_threads * 2u) {
            continue;
        }
        constexpr int iterations = 220000;
        std::vector<std::thread> threads;
        std::vector<uint64_t> outputs(static_cast<size_t>(thread_count), 0);
        const auto start = std::chrono::steady_clock::now();
        for (int i = 0; i < thread_count; ++i) {
            threads.emplace_back(ThreadSpinWork, iterations, i + 1, &outputs[static_cast<size_t>(i)]);
        }
        for (auto& thread : threads) {
            thread.join();
        }
        const auto end = std::chrono::steady_clock::now();
        const double ms = std::chrono::duration<double, std::milli>(end - start).count();
        uint64_t checksum = 0;
        for (uint64_t value : outputs) checksum ^= value;
        if (!first_case) out << ",";
        first_case = false;
        out << "{\"threads\":" << thread_count << ",\"iterations_per_thread\":" << iterations
            << ",\"latency_ms\":" << std::fixed << std::setprecision(6) << ms
            << ",\"work_items_per_second\":" << (ms > 0.0 ? (static_cast<double>(thread_count) * iterations * 1000.0 / ms) : 0.0)
            << ",\"checksum\":" << checksum << "}";
    }
    out << "],";
    out << "\"warnings\":[\"thread scaling is a short app-process probe and not a scheduler guarantee\"]";
    out << "}";
    return out.str();
}

std::string MemoryCaseJson(size_t bytes, int iterations) {
    std::vector<uint8_t> src(bytes);
    std::vector<uint8_t> dst(bytes);
    for (size_t i = 0; i < bytes; ++i) src[i] = static_cast<uint8_t>((i * 17 + 5) & 0xFF);
    uint64_t checksum = 0;
    const auto start = std::chrono::steady_clock::now();
    for (int it = 0; it < iterations; ++it) {
        std::copy(src.begin(), src.end(), dst.begin());
        checksum += dst[static_cast<size_t>(it) % bytes];
    }
    const auto end = std::chrono::steady_clock::now();
    const double ms = std::chrono::duration<double, std::milli>(end - start).count();
    const double mib = static_cast<double>(bytes) * static_cast<double>(iterations) / (1024.0 * 1024.0);
    g_phase6_sink ^= checksum;
    std::ostringstream out;
    out << std::fixed << std::setprecision(6);
    out << "{\"bytes\":" << bytes << ",\"iterations\":" << iterations
        << ",\"latency_ms\":" << ms
        << ",\"bandwidth_mib_per_second\":" << (ms > 0.0 ? (mib * 1000.0 / ms) : 0.0)
        << ",\"checksum\":" << checksum << "}";
    return out.str();
}

std::string MemoryProbeJson() {
    const std::vector<std::pair<size_t, int>> cases = {
            {4 * 1024, 2000},
            {64 * 1024, 800},
            {1024 * 1024, 120},
            {4 * 1024 * 1024, 24},
    };
    std::ostringstream out;
    out << "{\"copy_bandwidth_cases\":[";
    for (size_t i = 0; i < cases.size(); ++i) {
        if (i) out << ",";
        out << MemoryCaseJson(cases[i].first, cases[i].second);
    }
    out << "],\"warnings\":[\"memory probe uses bounded app-private buffers only\"]}";
    return out.str();
}

std::string BackendLoadProbeJson(const std::string& backend, const std::string& library_name) {
    dlerror();
    void* handle = dlopen(library_name.c_str(), RTLD_LAZY | RTLD_LOCAL);
    const char* error = dlerror();
    std::ostringstream out;
    out << "{\"backend\":\"" << JsonEscape(backend) << "\",";
    out << "\"library\":\"" << JsonEscape(library_name) << "\",";
    if (handle != nullptr) {
        out << "\"status\":\"loaded\",\"loaded\":true";
        dlclose(handle);
    } else {
        out << "\"status\":\"not_loaded\",\"loaded\":false,\"error\":\"" << JsonEscape(error ? error : "unknown dlopen error") << "\"";
    }
    out << "}";
    return out.str();
}

std::string BackendLoadJson() {
    const std::vector<std::pair<std::string, std::string>> probes = {
            {"vulkan", "libvulkan.so"},
            {"nnapi", "libneuralnetworks.so"},
            {"qnn", "libQnnSystem.so"},
            {"qnn", "libQnnHtp.so"},
            {"qnn", "libQnnCpu.so"},
            {"qnn", "libQnnGpu.so"},
            {"qnn", "libQnnDsp.so"},
            {"dsp_rpc", "libcdsprpc.so"},
            {"dsp_rpc", "libadsprpc.so"},
            {"snpe", "libSNPE.so"},
    };
    std::ostringstream out;
    out << "{\"probes\":[";
    for (size_t i = 0; i < probes.size(); ++i) {
        if (i) out << ",";
        out << BackendLoadProbeJson(probes[i].first, probes[i].second);
    }
    out << "],\"warnings\":[\"dlopen probes only test library loadability; they do not execute accelerator kernels\"]}";
    return out.str();
}

float DeterministicValue(int index, float scale) {
    const int wrapped = (index * 37 + 17) % 97;
    return (static_cast<float>(wrapped) - 48.0f) * scale;
}

uint8_t PackInt4Pair(int low, int high) {
    return static_cast<uint8_t>((low & 0x0F) | ((high & 0x0F) << 4));
}

int DecodeInt4(uint8_t nibble) {
    int value = static_cast<int>(nibble & 0x0F);
    return value >= 8 ? value - 16 : value;
}

void Int4DequantMatvecKernel(const std::vector<uint8_t>& packed, const std::vector<float>& scales,
                             const std::vector<float>& vector, std::vector<float>& output,
                             int rows, int cols) {
    for (int r = 0; r < rows; ++r) {
        float acc = 0.0f;
        for (int c = 0; c < cols; ++c) {
            const uint8_t byte = packed[(r * cols + c) / 2];
            const int q = DecodeInt4((c & 1) == 0 ? byte : static_cast<uint8_t>(byte >> 4));
            acc += static_cast<float>(q) * scales[r] * vector[c];
        }
        output[r] = acc;
    }
}

std::string QuantizationFixtureJson() {
    constexpr int rows = 8;
    constexpr int cols = 16;
    std::vector<float> weights(rows * cols);
    std::vector<float> vector(cols);
    std::vector<float> scales(rows);
    std::vector<int> q(rows * cols);
    std::vector<uint8_t> packed((rows * cols) / 2);
    std::vector<double> packed_reference(rows, 0.0);
    std::vector<double> original_reference(rows, 0.0);
    std::vector<float> output(rows, 0.0f);

    for (int i = 0; i < rows * cols; ++i) weights[i] = DeterministicValue(i + 700, 0.037f);
    for (int i = 0; i < cols; ++i) vector[i] = DeterministicValue(i + 900, 0.023f);
    for (int r = 0; r < rows; ++r) {
        float max_abs = 0.0f;
        for (int c = 0; c < cols; ++c) max_abs = std::max(max_abs, std::abs(weights[r * cols + c]));
        scales[r] = std::max(max_abs / 7.0f, 1.0e-6f);
        for (int c = 0; c < cols; ++c) {
            const int idx = r * cols + c;
            int value = static_cast<int>(std::round(weights[idx] / scales[r]));
            value = std::max(-8, std::min(7, value));
            q[idx] = value;
        }
    }
    for (int i = 0; i < rows * cols; i += 2) packed[i / 2] = PackInt4Pair(q[i], q[i + 1]);
    for (int r = 0; r < rows; ++r) {
        for (int c = 0; c < cols; ++c) {
            packed_reference[r] += static_cast<double>(q[r * cols + c]) * scales[r] * vector[c];
            original_reference[r] += static_cast<double>(weights[r * cols + c]) * vector[c];
        }
    }
    Int4DequantMatvecKernel(packed, scales, vector, output, rows, cols);
    double packed_max_error = 0.0;
    double quantization_max_error = 0.0;
    for (int r = 0; r < rows; ++r) {
        packed_max_error = std::max(packed_max_error, std::abs(static_cast<double>(output[r]) - packed_reference[r]));
        quantization_max_error = std::max(quantization_max_error, std::abs(packed_reference[r] - original_reference[r]));
    }

    std::ostringstream out;
    out << std::fixed << std::setprecision(8);
    out << "{";
    out << "\"name\":\"qwen_like_linear_int4_fixture\",";
    out << "\"shape\":{\"rows\":8,\"cols\":16,\"group_size\":16},";
    out << "\"format\":{\"signed\":true,\"bits\":4,\"packing\":\"low_nibble_first\",\"scale\":\"per_row_symmetric\"},";
    out << "\"packed_byte_length\":" << packed.size() << ",";
    out << "\"packed_reference_max_abs_error\":" << packed_max_error << ",";
    out << "\"quantization_vs_fp32_max_abs_error\":" << quantization_max_error << ",";
    out << "\"correctness_passed\":" << JsonBool(packed_max_error < 1.0e-5) << ",";
    out << "\"warning\":\"fixture validates packing/dequant plumbing only; it is not a model accuracy claim\"";
    out << "}";
    return out.str();
}

std::string QuantizationJson() {
    return std::string("{\"fixtures\":[") + QuantizationFixtureJson() +
           "],\"warnings\":[\"quantization fixtures use tiny deterministic tensors only\"]}";
}

std::string RunPhase6CharacterizationJson() {
    std::ostringstream out;
    out << "{";
    out << "\"schema_version\":\"0.1\",";
    out << "\"source\":\"android-phase6-characterization\",";
    out << "\"backend\":\"" << kBackend << "\",";
    out << "\"native_library\":\"qpnpu_probe_native\",";
    out << "\"cpu_isa\":" << CpuIsaJson() << ",";
    out << "\"topology\":" << TopologyJson() << ",";
    out << "\"memory\":" << MemoryProbeJson() << ",";
    out << "\"backend_load\":" << BackendLoadJson() << ",";
    out << "\"quantization\":" << QuantizationJson() << ",";
    out << "\"warnings\":[";
    out << "\"Phase 6 characterization only; not Qwen 9B inference\",";
    out << "\"backend load probes do not execute NPU, QNN, NNAPI, or Vulkan kernels\",";
    out << "\"native CPU timings are harness signals, not performance target claims\"";
    out << "]";
    out << "}";
    return out.str();
}

}  // namespace

extern "C" JNIEXPORT jstring JNICALL
Java_com_qpnpu_trial_MainActivity_nativeRunPhase6Characterization(JNIEnv* env, jobject /* thiz */) {
    const std::string json = RunPhase6CharacterizationJson();
    return env->NewStringUTF(json.c_str());
}
