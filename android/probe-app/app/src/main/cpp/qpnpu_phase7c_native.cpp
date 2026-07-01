#include <jni.h>

#include <algorithm>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <csetjmp>
#include <csignal>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <functional>
#include <iomanip>
#include <numeric>
#include <sstream>
#include <string>
#include <vector>

#if defined(__aarch64__)
#include <arm_neon.h>
#endif

namespace {

constexpr const char* kBackend = "cpu_android_generated_candidate";
constexpr const char* kGeneratorName = "qpnpu_phase7c_static_generator";
constexpr const char* kGeneratorVersion = "0.1";
constexpr const char* kKernelConfigHash = "phase7c_generated_native_candidates_v1";
volatile float g_phase7c_sink = 0.0f;

#if defined(__clang__) && defined(__aarch64__)
#define QPNPU_TARGET_DOTPROD __attribute__((target("+dotprod")))
#define QPNPU_TARGET_I8MM __attribute__((target("+i8mm")))
#define QPNPU_TARGET_BF16 __attribute__((target("+bf16")))
#define QPNPU_TARGET_SVE __attribute__((target("+sve")))
#else
#define QPNPU_TARGET_DOTPROD
#define QPNPU_TARGET_I8MM
#define QPNPU_TARGET_BF16
#define QPNPU_TARGET_SVE
#endif

sigjmp_buf g_sigill_env;
volatile sig_atomic_t g_sigill_guard_active = 0;

struct BenchStats {
    double p50_ms = 0.0;
    double p90_ms = 0.0;
    double p99_ms = 0.0;
    double throughput = 0.0;
};

struct CandidateResult {
    std::string name;
    std::string op;
    std::string target_feature;
    std::string candidate_type;
    std::string shape_json;
    std::string status;
    std::string notes;
    bool compiled = true;
    bool reported = false;
    bool executed = false;
    bool sigill = false;
    bool correctness_passed = false;
    double max_abs_error = 0.0;
    uint64_t checksum = 0;
    BenchStats stats;
};

struct CandidateSpec {
    const char* name;
    const char* op;
    const char* target_feature;
    const char* candidate_type;
    const char* shape_json;
    const char* notes;
    bool compiled;
    bool experimental;
    CandidateResult (*run_fn)();
};

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
                        << static_cast<int>(static_cast<unsigned char>(ch)) << std::dec << std::setfill(' ');
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

bool ContainsToken(const std::string& text, const std::string& token) {
    return text.find(token) != std::string::npos;
}

float DeterministicValue(int index, float scale) {
    const int wrapped = (index * 37 + 17) % 97;
    return (static_cast<float>(wrapped) - 48.0f) * scale;
}

BenchStats Measure(const std::function<void()>& fn, int iterations, double work_items) {
    std::vector<double> samples;
    samples.reserve(static_cast<size_t>(iterations));
    for (int i = 0; i < iterations; ++i) {
        const auto start = std::chrono::steady_clock::now();
        fn();
        const auto end = std::chrono::steady_clock::now();
        samples.push_back(std::chrono::duration<double, std::milli>(end - start).count());
    }
    std::sort(samples.begin(), samples.end());
    const auto percentile = [&](double p) -> double {
        if (samples.empty()) {
            return 0.0;
        }
        const double index = (p / 100.0) * static_cast<double>(samples.size() - 1);
        return samples[static_cast<size_t>(std::round(index))];
    };
    const double total_ms = std::accumulate(samples.begin(), samples.end(), 0.0);
    BenchStats stats;
    stats.p50_ms = percentile(50.0);
    stats.p90_ms = percentile(90.0);
    stats.p99_ms = percentile(99.0);
    stats.throughput = total_ms > 0.0 ? (work_items * static_cast<double>(iterations) * 1000.0 / total_ms) : 0.0;
    return stats;
}

void SigillHandler(int /*signum*/) {
    if (g_sigill_guard_active) {
        g_sigill_guard_active = 0;
        siglongjmp(g_sigill_env, 1);
    }
}

CandidateResult RunWithSigillGuard(const CandidateSpec& spec) {
    CandidateResult result;
    result.name = spec.name;
    result.op = spec.op;
    result.target_feature = spec.target_feature;
    result.candidate_type = spec.candidate_type;
    result.shape_json = spec.shape_json;
    result.notes = spec.notes;
    result.compiled = spec.compiled;

    if (!spec.compiled || spec.run_fn == nullptr) {
        result.status = "not_compiled";
        return result;
    }

    struct sigaction old_action;
    struct sigaction action;
    std::memset(&old_action, 0, sizeof(old_action));
    std::memset(&action, 0, sizeof(action));
    action.sa_handler = SigillHandler;
    sigemptyset(&action.sa_mask);
    action.sa_flags = 0;

    if (sigaction(SIGILL, &action, &old_action) != 0) {
        result.status = "guard_install_failed";
        result.notes += "; SIGILL guard install failed: ";
        result.notes += std::strerror(errno);
        return result;
    }

    if (sigsetjmp(g_sigill_env, 1) == 0) {
        g_sigill_guard_active = 1;
        result = spec.run_fn();
        result.name = spec.name;
        result.op = spec.op;
        result.target_feature = spec.target_feature;
        result.candidate_type = spec.candidate_type;
        result.shape_json = spec.shape_json;
        result.notes = spec.notes;
        result.compiled = spec.compiled;
        result.executed = true;
        result.sigill = false;
        result.status = result.correctness_passed ? "passed_correctness" : "failed_correctness";
        g_sigill_guard_active = 0;
    } else {
        result.sigill = true;
        result.executed = true;
        result.status = "sigill";
        result.notes = std::string(spec.notes) + "; SIGILL caught while executing generated candidate";
    }

    sigaction(SIGILL, &old_action, nullptr);
    g_sigill_guard_active = 0;
    return result;
}

CandidateResult MakeSkipped(const CandidateSpec& spec, const std::string& status, bool reported) {
    CandidateResult result;
    result.name = spec.name;
    result.op = spec.op;
    result.target_feature = spec.target_feature;
    result.candidate_type = spec.candidate_type;
    result.shape_json = spec.shape_json;
    result.notes = spec.notes;
    result.compiled = spec.compiled;
    result.reported = reported;
    result.executed = false;
    result.status = status;
    return result;
}

uint64_t ChecksumFloats(const std::vector<float>& values) {
    uint64_t checksum = 1469598103934665603ULL;
    for (float value : values) {
        uint32_t bits = 0;
        std::memcpy(&bits, &value, sizeof(bits));
        checksum ^= static_cast<uint64_t>(bits);
        checksum *= 1099511628211ULL;
    }
    return checksum;
}

void ScalarMatvec(const std::vector<float>& matrix, const std::vector<float>& vector,
                  std::vector<float>& output, int rows, int cols) {
    for (int r = 0; r < rows; ++r) {
        float acc = 0.0f;
        for (int c = 0; c < cols; ++c) {
            acc += matrix[static_cast<size_t>(r) * cols + c] * vector[static_cast<size_t>(c)];
        }
        output[static_cast<size_t>(r)] = acc;
    }
}

CandidateResult RunScalarMatvecGenerated() {
    constexpr int rows = 8;
    constexpr int cols = 16;
    std::vector<float> matrix(rows * cols);
    std::vector<float> vector(cols);
    std::vector<float> output(rows);
    std::vector<double> reference(rows);
    for (int i = 0; i < rows * cols; ++i) matrix[static_cast<size_t>(i)] = DeterministicValue(i, 0.013f);
    for (int i = 0; i < cols; ++i) vector[static_cast<size_t>(i)] = DeterministicValue(i + 100, 0.017f);
    for (int r = 0; r < rows; ++r) {
        double acc = 0.0;
        for (int c = 0; c < cols; ++c) acc += static_cast<double>(matrix[static_cast<size_t>(r) * cols + c]) * vector[static_cast<size_t>(c)];
        reference[static_cast<size_t>(r)] = acc;
    }
    ScalarMatvec(matrix, vector, output, rows, cols);
    double max_error = 0.0;
    for (int r = 0; r < rows; ++r) max_error = std::max(max_error, std::abs(static_cast<double>(output[static_cast<size_t>(r)]) - reference[static_cast<size_t>(r)]));
    CandidateResult result;
    result.correctness_passed = max_error < 1.0e-4;
    result.max_abs_error = max_error;
    result.checksum = ChecksumFloats(output);
    result.stats = Measure([&]() {
        ScalarMatvec(matrix, vector, output, rows, cols);
        g_phase7c_sink += output[0] * 1.0e-12f;
    }, 250, static_cast<double>(rows));
    return result;
}

void AsimdMatvec(const std::vector<float>& matrix, const std::vector<float>& vector,
                 std::vector<float>& output, int rows, int cols) {
#if defined(__aarch64__)
    for (int r = 0; r < rows; ++r) {
        float32x4_t acc = vdupq_n_f32(0.0f);
        for (int c = 0; c < cols; c += 4) {
            const float32x4_t m = vld1q_f32(&matrix[static_cast<size_t>(r) * cols + c]);
            const float32x4_t v = vld1q_f32(&vector[static_cast<size_t>(c)]);
            acc = vfmaq_f32(acc, m, v);
        }
        output[static_cast<size_t>(r)] = vaddvq_f32(acc);
    }
#else
    ScalarMatvec(matrix, vector, output, rows, cols);
#endif
}

CandidateResult RunAsimdMatvecGenerated() {
    constexpr int rows = 8;
    constexpr int cols = 16;
    std::vector<float> matrix(rows * cols);
    std::vector<float> vector(cols);
    std::vector<float> output(rows);
    std::vector<double> reference(rows);
    for (int i = 0; i < rows * cols; ++i) matrix[static_cast<size_t>(i)] = DeterministicValue(i + 200, 0.015f);
    for (int i = 0; i < cols; ++i) vector[static_cast<size_t>(i)] = DeterministicValue(i + 300, 0.011f);
    for (int r = 0; r < rows; ++r) {
        double acc = 0.0;
        for (int c = 0; c < cols; ++c) acc += static_cast<double>(matrix[static_cast<size_t>(r) * cols + c]) * vector[static_cast<size_t>(c)];
        reference[static_cast<size_t>(r)] = acc;
    }
    AsimdMatvec(matrix, vector, output, rows, cols);
    double max_error = 0.0;
    for (int r = 0; r < rows; ++r) max_error = std::max(max_error, std::abs(static_cast<double>(output[static_cast<size_t>(r)]) - reference[static_cast<size_t>(r)]));
    CandidateResult result;
    result.correctness_passed = max_error < 1.0e-4;
    result.max_abs_error = max_error;
    result.checksum = ChecksumFloats(output);
    result.stats = Measure([&]() {
        AsimdMatvec(matrix, vector, output, rows, cols);
        g_phase7c_sink += output[0] * 1.0e-12f;
    }, 250, static_cast<double>(rows));
    return result;
}

#if defined(__aarch64__)
QPNPU_TARGET_DOTPROD uint64_t DotprodFixture() {
    uint32_t out = 0;
    asm volatile(
        "movi v0.4s, #0\n"
        "movi v1.16b, #1\n"
        "movi v2.16b, #2\n"
        "udot v0.4s, v1.16b, v2.16b\n"
        "umov %w[out], v0.s[0]\n"
        : [out] "=r"(out)
        :
        : "v0", "v1", "v2");
    return static_cast<uint64_t>(out);
}

QPNPU_TARGET_I8MM uint64_t I8mmFixture() {
    uint32_t out = 0;
    asm volatile(
        "movi v0.4s, #0\n"
        "movi v1.16b, #1\n"
        "movi v2.16b, #2\n"
        "smmla v0.4s, v1.16b, v2.16b\n"
        "umov %w[out], v0.s[0]\n"
        : [out] "=r"(out)
        :
        : "v0", "v1", "v2");
    return static_cast<uint64_t>(out);
}

QPNPU_TARGET_BF16 uint64_t Bf16Fixture() {
    uint32_t out = 0;
    asm volatile(
        "movi v0.4s, #0\n"
        "movi v1.8h, #0\n"
        "movi v2.8h, #0\n"
        "bfdot v0.4s, v1.8h, v2.8h\n"
        "umov %w[out], v0.s[0]\n"
        : [out] "=r"(out)
        :
        : "v0", "v1", "v2");
    return static_cast<uint64_t>(out);
}

QPNPU_TARGET_SVE uint64_t SveVectorLengthFixture() {
    uint64_t out = 0;
    asm volatile(
        "rdvl %[out], #1\n"
        : [out] "=r"(out));
    return out;
}
#else
uint64_t DotprodFixture() { return 0; }
uint64_t I8mmFixture() { return 0; }
uint64_t Bf16Fixture() { return 0; }
uint64_t SveVectorLengthFixture() { return 0; }
#endif

BenchStats MeasureChecksumFn(uint64_t (*fn)(), int iterations, uint64_t& checksum) {
    std::vector<double> samples;
    samples.reserve(static_cast<size_t>(iterations));
    uint64_t local = 0;
    for (int i = 0; i < iterations; ++i) {
        const auto start = std::chrono::steady_clock::now();
        local ^= fn() + static_cast<uint64_t>(i);
        const auto end = std::chrono::steady_clock::now();
        samples.push_back(std::chrono::duration<double, std::milli>(end - start).count());
    }
    checksum ^= local;
    std::sort(samples.begin(), samples.end());
    const double total_ms = std::accumulate(samples.begin(), samples.end(), 0.0);
    const auto percentile = [&](double p) -> double {
        if (samples.empty()) return 0.0;
        const double index = (p / 100.0) * static_cast<double>(samples.size() - 1);
        return samples[static_cast<size_t>(std::round(index))];
    };
    BenchStats stats;
    stats.p50_ms = percentile(50.0);
    stats.p90_ms = percentile(90.0);
    stats.p99_ms = percentile(99.0);
    stats.throughput = total_ms > 0.0 ? (static_cast<double>(iterations) * 1000.0 / total_ms) : 0.0;
    return stats;
}

CandidateResult RunDotprodGenerated() {
    const uint64_t value = DotprodFixture();
    CandidateResult result;
    result.correctness_passed = value == 8ULL;
    result.max_abs_error = result.correctness_passed ? 0.0 : std::abs(static_cast<double>(value) - 8.0);
    result.checksum = value;
    result.stats = MeasureChecksumFn(DotprodFixture, 500, result.checksum);
    return result;
}

CandidateResult RunI8mmGenerated() {
    const uint64_t value = I8mmFixture();
    CandidateResult result;
    result.correctness_passed = value == 16ULL;
    result.max_abs_error = result.correctness_passed ? 0.0 : std::abs(static_cast<double>(value) - 16.0);
    result.checksum = value;
    result.stats = MeasureChecksumFn(I8mmFixture, 500, result.checksum);
    return result;
}

CandidateResult RunBf16Generated() {
    const uint64_t value = Bf16Fixture();
    CandidateResult result;
    result.correctness_passed = value == 0ULL;
    result.max_abs_error = static_cast<double>(value);
    result.checksum = value;
    result.stats = MeasureChecksumFn(Bf16Fixture, 500, result.checksum);
    return result;
}

CandidateResult RunSveVectorLengthGenerated() {
    const uint64_t value = SveVectorLengthFixture();
    CandidateResult result;
    result.correctness_passed = value >= 16ULL && (value % 16ULL) == 0ULL;
    result.max_abs_error = result.correctness_passed ? 0.0 : 1.0;
    result.checksum = value;
    result.stats = MeasureChecksumFn(SveVectorLengthFixture, 500, result.checksum);
    return result;
}

std::vector<CandidateSpec> BuildCandidateSpecs() {
    return {
        {"generated_scalar_fp32_matvec_v1", "fp32_matvec", "scalar", "generated_scalar", "{\"rows\":8,\"cols\":16}",
         "portable generated scalar baseline; always safe to execute", true, false, RunScalarMatvecGenerated},
        {"generated_asimd_fp32_matvec_4lane_v1", "fp32_matvec", "asimd", "generated_asimd", "{\"rows\":8,\"cols\":16,\"lanes\":4}",
         "NEON/ASIMD generated candidate gated by reported ASIMD", true, false, RunAsimdMatvecGenerated},
        {"generated_asimddp_udot_tile_v1", "int8_dot_tile", "asimddp", "generated_dotprod", "{\"lanes\":16,\"accumulators\":4}",
         "tiny UDOT tile candidate gated by reported ASIMDDP", true, false, RunDotprodGenerated},
        {"generated_i8mm_smmla_tile_v1", "int8_matrix_tile", "i8mm", "generated_i8mm", "{\"m\":2,\"n\":2,\"k\":8}",
         "tiny SMMLA tile candidate gated by reported I8MM", true, false, RunI8mmGenerated},
        {"generated_bf16_bfdot_tile_v1", "bf16_dot_tile", "bf16", "generated_bf16", "{\"lanes\":8,\"accumulators\":4}",
         "tiny BFDOT tile candidate gated by reported BF16", true, false, RunBf16Generated},
        {"generated_sve_vector_length_tile_selector_v1", "sve_tile_selector", "sve", "generated_sve", "{\"rdvl_multiplier\":1}",
         "SVE vector-length query used to parameterize later generated kernels", true, false, RunSveVectorLengthGenerated},
        {"experimental_sve2_candidate_v1", "sve2_kernel_candidate", "sve2", "experimental_deferred", "{\"reason\":\"needs isolated SVE2 kernel fixture\"}",
         "reported on the target but deferred until an isolated SVE2 generated kernel fixture is added", false, true, nullptr},
        {"experimental_svei8mm_candidate_v1", "svei8mm_kernel_candidate", "svei8mm", "experimental_deferred", "{\"reason\":\"needs isolated SVE I8MM kernel fixture\"}",
         "reported on the target but deferred until an isolated SVE I8MM fixture is added", false, true, nullptr},
        {"experimental_sme_candidate_v1", "sme_kernel_candidate", "sme", "experimental_deferred", "{\"reason\":\"SME streaming mode intentionally not entered in same-process harness\"}",
         "reported on the target but deferred; entering SME streaming mode needs stricter process isolation", false, true, nullptr},
    };
}

bool FeatureReported(const std::string& cpuinfo, const std::string& feature) {
    if (feature == "scalar") {
        return true;
    }
    return ContainsToken(cpuinfo, feature);
}

std::vector<CandidateResult> RunCandidates() {
    const std::string cpuinfo = ReadSmallTextFile("/proc/cpuinfo", 128 * 1024);
    std::vector<CandidateResult> results;
    for (const CandidateSpec& spec : BuildCandidateSpecs()) {
        const bool reported = FeatureReported(cpuinfo, spec.target_feature);
        CandidateResult result;
        if (spec.experimental) {
            result = MakeSkipped(spec, "deferred_no_safe_kernel", reported);
        } else if (!reported) {
            result = MakeSkipped(spec, "skipped_feature_not_reported", reported);
        } else {
            result = RunWithSigillGuard(spec);
            result.reported = reported;
        }
        results.push_back(result);
    }
    return results;
}

std::string CandidateJson(const CandidateResult& item) {
    std::ostringstream out;
    out << std::fixed << std::setprecision(6);
    out << "{";
    out << "\"name\":\"" << JsonEscape(item.name) << "\",";
    out << "\"operator\":\"" << JsonEscape(item.op) << "\",";
    out << "\"target_feature\":\"" << JsonEscape(item.target_feature) << "\",";
    out << "\"candidate_type\":\"" << JsonEscape(item.candidate_type) << "\",";
    out << "\"compiled\":" << JsonBool(item.compiled) << ",";
    out << "\"reported\":" << JsonBool(item.reported) << ",";
    out << "\"executed\":" << JsonBool(item.executed) << ",";
    out << "\"sigill\":" << JsonBool(item.sigill) << ",";
    out << "\"status\":\"" << JsonEscape(item.status) << "\",";
    out << "\"shape\":" << item.shape_json << ",";
    out << "\"correctness\":{\"passed\":" << JsonBool(item.correctness_passed)
        << ",\"max_abs_error\":" << item.max_abs_error
        << ",\"checksum\":" << item.checksum << "},";
    if (item.executed && !item.sigill) {
        out << "\"benchmark\":{";
        out << "\"schema_version\":\"0.1\",";
        out << "\"timestamp_utc\":\"native_clock_unavailable\",";
        out << "\"device\":{\"type\":\"android_device\"},";
        out << "\"model\":{\"architecture\":\"generated_kernel_fixture\",\"hf_id\":\"none\"},";
        out << "\"backend\":\"" << kBackend << "\",";
        out << "\"operator\":\"" << JsonEscape(item.op) << "\",";
        out << "\"shape\":" << item.shape_json << ",";
        out << "\"metrics\":{";
        out << "\"latency_ms_p50\":" << item.stats.p50_ms << ",";
        out << "\"latency_ms_p90\":" << item.stats.p90_ms << ",";
        out << "\"latency_ms_p99\":" << item.stats.p99_ms << ",";
        out << "\"tokens_per_second\":" << item.stats.throughput << ",";
        out << "\"memory_rss_mb\":0.0,";
        out << "\"correctness_passed\":" << JsonBool(item.correctness_passed) << "},";
        out << "\"thermal\":{},";
        out << "\"kernel_config_hash\":\"" << kKernelConfigHash << ":" << JsonEscape(item.name) << "\",";
        out << "\"warnings\":[\"generated Android CPU candidate only; not Qwen 9B; not NPU; not a performance claim\"]";
        out << "},";
    }
    out << "\"warnings\":[";
    out << "\"generated kernel candidate only\",";
    out << "\"CPU app-process execution only; not QNN, NPU, NNAPI, or Vulkan\",";
    out << "\"not a Qwen 9B inference path\",";
    out << "\"not a performance target claim\"";
    out << "],";
    out << "\"notes\":\"" << JsonEscape(item.notes) << "\"";
    out << "}";
    return out.str();
}

std::string BuildPhase7CJson() {
    const std::vector<CandidateResult> candidates = RunCandidates();
    int executed_count = 0;
    int passed_count = 0;
    int sigill_count = 0;
    int skipped_count = 0;
    int deferred_count = 0;
    int experimental_count = 0;
    bool all_executed_correct = true;
    for (const CandidateResult& candidate : candidates) {
        if (candidate.executed) ++executed_count;
        if (candidate.correctness_passed) ++passed_count;
        if (candidate.sigill) ++sigill_count;
        if (candidate.status == "skipped_feature_not_reported" || candidate.status == "not_compiled") ++skipped_count;
        if (candidate.status == "deferred_no_safe_kernel") ++deferred_count;
        if (candidate.candidate_type.find("experimental") != std::string::npos) ++experimental_count;
        if (candidate.executed && !candidate.correctness_passed) all_executed_correct = false;
    }

    std::ostringstream out;
    out << std::fixed << std::setprecision(6);
    out << "{";
    out << "\"schema_version\":\"0.1\",";
    out << "\"source\":\"android-phase7c-generated-kernels\",";
    out << "\"backend\":\"" << kBackend << "\",";
    out << "\"native_library\":\"qpnpu_probe_native\",";
    out << "\"generator\":{\"name\":\"" << kGeneratorName << "\",\"version\":\"" << kGeneratorVersion
        << "\",\"kernel_config_hash\":\"" << kKernelConfigHash << "\",\"selection_source\":\"Phase 7A executed_ok ISA features plus deferred experimental features\"},";
    out << "\"safety\":{\"uses_sigill_guard\":true,\"executes_only_reported_features\":true,"
        << "\"destructive_unreported_feature_trials\":false,\"experimental_candidates_are_deferred\":true,"
        << "\"process_isolation\":false},";
    out << "\"candidates\":[";
    for (size_t i = 0; i < candidates.size(); ++i) {
        if (i) out << ",";
        out << CandidateJson(candidates[i]);
    }
    out << "],";
    out << "\"summary\":{\"candidate_count\":" << candidates.size()
        << ",\"executed_count\":" << executed_count
        << ",\"passed_count\":" << passed_count
        << ",\"sigill_count\":" << sigill_count
        << ",\"skipped_count\":" << skipped_count
        << ",\"deferred_count\":" << deferred_count
        << ",\"experimental_count\":" << experimental_count
        << ",\"all_executed_correctness_passed\":" << JsonBool(all_executed_correct) << "},";
    out << "\"warnings\":[";
    out << "\"Phase 7C generated kernel candidates are tiny CPU fixtures only; not Qwen 9B inference\",";
    out << "\"not QNN, NPU, NNAPI, or Vulkan execution\",";
    out << "\"latency fields are smoke telemetry, not a performance target claim\",";
    out << "\"SVE2, SVEI8MM, and SME candidates are listed but deferred until safer isolated probes exist\"";
    out << "]";
    out << "}";
    return out.str();
}

}  // namespace

extern "C" JNIEXPORT jstring JNICALL
Java_com_qpnpu_trial_MainActivity_nativeRunPhase7CGeneratedKernels(JNIEnv* env, jobject /* thiz */) {
    const std::string json = BuildPhase7CJson();
    return env->NewStringUTF(json.c_str());
}