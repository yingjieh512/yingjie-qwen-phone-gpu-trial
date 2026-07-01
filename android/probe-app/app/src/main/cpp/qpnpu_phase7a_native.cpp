#include <jni.h>

#include <cerrno>
#include <csetjmp>
#include <csignal>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <string>
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

using ProbeFn = uint64_t (*)();

#if defined(__clang__) && defined(__aarch64__)
#define QPNPU_TARGET_CRC __attribute__((target("+crc")))
#define QPNPU_TARGET_DOTPROD __attribute__((target("+dotprod")))
#define QPNPU_TARGET_I8MM __attribute__((target("+i8mm")))
#define QPNPU_TARGET_BF16 __attribute__((target("+bf16")))
#define QPNPU_TARGET_SVE __attribute__((target("+sve")))
#else
#define QPNPU_TARGET_CRC
#define QPNPU_TARGET_DOTPROD
#define QPNPU_TARGET_I8MM
#define QPNPU_TARGET_BF16
#define QPNPU_TARGET_SVE
#endif

sigjmp_buf g_sigill_env;
volatile sig_atomic_t g_sigill_guard_active = 0;

struct GuardedProbeResult {
    bool guard_installed = false;
    bool executed = false;
    bool sigill = false;
    std::string status;
    std::string error;
    uint64_t checksum = 0;
};

struct FeatureSpec {
    const char* feature_name;
    const char* cpuinfo_token;
    const char* auxv_register;
    uint64_t auxv_mask;
    bool auxv_macro_available;
    const char* probe_id;
    bool compiled;
    ProbeFn probe_fn;
    const char* notes;
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

void SigillHandler(int /*signum*/) {
    if (g_sigill_guard_active) {
        g_sigill_guard_active = 0;
        siglongjmp(g_sigill_env, 1);
    }
}

GuardedProbeResult RunWithSigillGuard(ProbeFn probe_fn) {
    GuardedProbeResult result;
    if (probe_fn == nullptr) {
        result.status = "not_compiled";
        result.error = "probe function is null";
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
        result.error = std::strerror(errno);
        return result;
    }
    result.guard_installed = true;

    if (sigsetjmp(g_sigill_env, 1) == 0) {
        g_sigill_guard_active = 1;
        result.checksum = probe_fn();
        g_sigill_guard_active = 0;
        result.executed = true;
        result.status = "executed_ok";
    } else {
        result.sigill = true;
        result.executed = true;
        result.status = "sigill";
        result.error = "SIGILL caught while executing guarded instruction probe";
    }

    if (sigaction(SIGILL, &old_action, nullptr) != 0 && result.error.empty()) {
        result.error = std::strerror(errno);
    }
    g_sigill_guard_active = 0;
    return result;
}

#if defined(__aarch64__)

uint64_t ProbeAsimdNeonAdd() {
    uint32_t out = 0;
    asm volatile(
        "movi v0.4s, #1\n"
        "add v0.4s, v0.4s, v0.4s\n"
        "umov %w[out], v0.s[0]\n"
        : [out] "=r"(out)
        :
        : "v0");
    return static_cast<uint64_t>(out);
}

QPNPU_TARGET_CRC uint64_t ProbeCrc32cx() {
    uint32_t crc = 0x12345678u;
    const uint64_t value = 0x1020304050607080ULL;
    asm volatile(
        "crc32cx %w[crc], %w[crc], %x[value]\n"
        : [crc] "+r"(crc)
        : [value] "r"(value));
    return static_cast<uint64_t>(crc);
}

QPNPU_TARGET_DOTPROD uint64_t ProbeDotProductUdot() {
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

QPNPU_TARGET_I8MM uint64_t ProbeI8mmSmmla() {
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

QPNPU_TARGET_BF16 uint64_t ProbeBf16Bfdot() {
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

QPNPU_TARGET_SVE uint64_t ProbeSveVectorLength() {
    uint64_t out = 0;
    asm volatile(
        "rdvl %[out], #1\n"
        : [out] "=r"(out));
    return out;
}

#else

uint64_t ProbeAsimdNeonAdd() { return 0; }
QPNPU_TARGET_CRC uint64_t ProbeCrc32cx() { return 0; }
QPNPU_TARGET_DOTPROD uint64_t ProbeDotProductUdot() { return 0; }
QPNPU_TARGET_I8MM uint64_t ProbeI8mmSmmla() { return 0; }
QPNPU_TARGET_BF16 uint64_t ProbeBf16Bfdot() { return 0; }
QPNPU_TARGET_SVE uint64_t ProbeSveVectorLength() { return 0; }

#endif

std::vector<FeatureSpec> BuildFeatureSpecs() {
    return {
#ifdef HWCAP_ASIMD
        {"asimd", "asimd", "AT_HWCAP", static_cast<uint64_t>(HWCAP_ASIMD), true,
         "asimd_neon_add", true, ProbeAsimdNeonAdd, "baseline NEON add fixture"},
#else
        {"asimd", "asimd", "AT_HWCAP", 0, false,
         "asimd_neon_add", true, ProbeAsimdNeonAdd, "baseline NEON add fixture; auxv macro unavailable"},
#endif
#ifdef HWCAP_CRC32
        {"crc32", "crc32", "AT_HWCAP", static_cast<uint64_t>(HWCAP_CRC32), true,
         "crc32cx_scalar", true, ProbeCrc32cx, "scalar CRC32 instruction fixture"},
#else
        {"crc32", "crc32", "AT_HWCAP", 0, false,
         "crc32cx_scalar", true, ProbeCrc32cx, "scalar CRC32 instruction fixture; auxv macro unavailable"},
#endif
#ifdef HWCAP_ASIMDDP
        {"asimddp", "asimddp", "AT_HWCAP", static_cast<uint64_t>(HWCAP_ASIMDDP), true,
         "asimddp_udot", true, ProbeDotProductUdot, "int8 dot-product instruction fixture"},
#else
        {"asimddp", "asimddp", "AT_HWCAP", 0, false,
         "asimddp_udot", true, ProbeDotProductUdot, "int8 dot-product instruction fixture; auxv macro unavailable"},
#endif
#ifdef HWCAP2_I8MM
        {"i8mm", "i8mm", "AT_HWCAP2", static_cast<uint64_t>(HWCAP2_I8MM), true,
         "i8mm_smmla", true, ProbeI8mmSmmla, "matrix multiply accumulate instruction fixture"},
#else
        {"i8mm", "i8mm", "AT_HWCAP2", 0, false,
         "i8mm_smmla", true, ProbeI8mmSmmla, "matrix multiply accumulate instruction fixture; auxv macro unavailable"},
#endif
#ifdef HWCAP2_BF16
        {"bf16", "bf16", "AT_HWCAP2", static_cast<uint64_t>(HWCAP2_BF16), true,
         "bf16_bfdot", true, ProbeBf16Bfdot, "BF16 dot-product instruction fixture"},
#else
        {"bf16", "bf16", "AT_HWCAP2", 0, false,
         "bf16_bfdot", true, ProbeBf16Bfdot, "BF16 dot-product instruction fixture; auxv macro unavailable"},
#endif
#ifdef HWCAP_SVE
        {"sve", "sve", "AT_HWCAP", static_cast<uint64_t>(HWCAP_SVE), true,
         "sve_rdvl", true, ProbeSveVectorLength, "SVE vector-length query fixture"},
#else
        {"sve", "sve", "AT_HWCAP", 0, false,
         "sve_rdvl", true, ProbeSveVectorLength, "SVE vector-length query fixture; auxv macro unavailable"},
#endif
#ifdef HWCAP2_SVE2
        {"sve2", "sve2", "AT_HWCAP2", static_cast<uint64_t>(HWCAP2_SVE2), true,
         "sve2_instruction_probe", false, nullptr, "reported only in 7A; SVE2 destructive probe deferred"},
#else
        {"sve2", "sve2", "AT_HWCAP2", 0, false,
         "sve2_instruction_probe", false, nullptr, "reported only in 7A; auxv macro unavailable or destructive probe deferred"},
#endif
#ifdef HWCAP2_SVEI8MM
        {"svei8mm", "svei8mm", "AT_HWCAP2", static_cast<uint64_t>(HWCAP2_SVEI8MM), true,
         "svei8mm_instruction_probe", false, nullptr, "reported only in 7A; SVE i8mm probe deferred"},
#else
        {"svei8mm", "svei8mm", "AT_HWCAP2", 0, false,
         "svei8mm_instruction_probe", false, nullptr, "reported only in 7A; auxv macro unavailable or probe deferred"},
#endif
#ifdef HWCAP2_SME
        {"sme", "sme", "AT_HWCAP2", static_cast<uint64_t>(HWCAP2_SME), true,
         "sme_state_probe", false, nullptr, "reported only in 7A; SME streaming-mode entry is deferred"},
#else
        {"sme", "sme", "AT_HWCAP2", 0, false,
         "sme_state_probe", false, nullptr, "reported only in 7A; auxv macro unavailable or probe deferred"},
#endif
    };
}

std::string ProbeJson(const FeatureSpec& spec, const std::string& cpuinfo,
                      uint64_t hwcap, uint64_t hwcap2,
                      int* executed_ok_count, int* sigill_count, int* skipped_count) {
    const uint64_t reg_value = std::string(spec.auxv_register) == "AT_HWCAP" ? hwcap : hwcap2;
    const bool cpuinfo_reported = TextContainsToken(cpuinfo, spec.cpuinfo_token);
    const bool auxv_reported = spec.auxv_macro_available && ((reg_value & spec.auxv_mask) != 0);
    const bool reported = cpuinfo_reported || auxv_reported;

    GuardedProbeResult guarded;
    bool executed = false;
    bool sigill = false;
    std::string status;
    std::string error;
    uint64_t checksum = 0;

#if defined(__aarch64__)
    if (!spec.compiled) {
        status = "deferred_no_safe_probe";
        ++(*skipped_count);
    } else if (!reported) {
        status = "skipped_not_reported";
        error = "feature was not reported by cpuinfo or auxv; 7A avoids intentionally destructive trials";
        ++(*skipped_count);
    } else {
        guarded = RunWithSigillGuard(spec.probe_fn);
        executed = guarded.executed;
        sigill = guarded.sigill;
        status = guarded.status;
        error = guarded.error;
        checksum = guarded.checksum;
        if (status == "executed_ok") {
            ++(*executed_ok_count);
        } else if (status == "sigill") {
            ++(*sigill_count);
        }
    }
#else
    status = "unsupported_host_arch";
    error = "Phase 7A instruction probes require an arm64 Android build";
    ++(*skipped_count);
#endif

    std::ostringstream out;
    out << "{";
    out << "\"feature_name\":\"" << JsonEscape(spec.feature_name) << "\",";
    out << "\"cpuinfo_token\":\"" << JsonEscape(spec.cpuinfo_token) << "\",";
    out << "\"cpuinfo_reported\":" << JsonBool(cpuinfo_reported) << ",";
    out << "\"auxv_macro_available\":" << JsonBool(spec.auxv_macro_available) << ",";
    out << "\"auxv_reported\":" << JsonBool(auxv_reported) << ",";
    out << "\"auxv_register\":\"" << JsonEscape(spec.auxv_register) << "\",";
    out << "\"reported\":" << JsonBool(reported) << ",";
    out << "\"probe_id\":\"" << JsonEscape(spec.probe_id) << "\",";
    out << "\"compiled\":" << JsonBool(spec.compiled) << ",";
    out << "\"guarded\":" << JsonBool(guarded.guard_installed) << ",";
    out << "\"executed\":" << JsonBool(executed) << ",";
    out << "\"sigill\":" << JsonBool(sigill) << ",";
    out << "\"status\":\"" << JsonEscape(status) << "\",";
    out << "\"checksum\":" << checksum << ",";
    out << "\"notes\":\"" << JsonEscape(spec.notes) << "\"";
    if (!error.empty()) {
        out << ",\"error\":\"" << JsonEscape(error) << "\"";
    }
    out << "}";
    return out.str();
}

std::string RunPhase7AIsaProbesJson() {
    const std::string cpuinfo = ReadSmallTextFile("/proc/cpuinfo", 65536);
    const uint64_t hwcap = SafeGetAuxv(AT_HWCAP);
    const uint64_t hwcap2 = SafeGetAuxv(AT_HWCAP2);
    const std::vector<FeatureSpec> specs = BuildFeatureSpecs();
    int executed_ok_count = 0;
    int sigill_count = 0;
    int skipped_count = 0;

    std::ostringstream out;
    out << "{";
    out << "\"schema_version\":\"0.1\",";
    out << "\"source\":\"android-phase7a-isa-probes\",";
    out << "\"backend\":\"" << kBackend << "\",";
    out << "\"native_library\":\"qpnpu_probe_native\",";
    out << "\"safety\":{";
    out << "\"strategy\":\"sigaction_sigsetjmp_same_process\",";
    out << "\"executes_only_reported_features\":true,";
    out << "\"destructive_unreported_feature_trials\":false,";
    out << "\"process_isolation\":false";
    out << "},";
    out << "\"cpu_evidence\":{";
    out << "\"proc_cpuinfo_readable\":" << JsonBool(!cpuinfo.empty()) << ",";
    out << "\"auxv\":{\"AT_HWCAP\":" << hwcap << ",\"AT_HWCAP2\":" << hwcap2 << "}";
    out << "},";
    out << "\"isa_probes\":[";
    for (size_t i = 0; i < specs.size(); ++i) {
        if (i) out << ",";
        out << ProbeJson(specs[i], cpuinfo, hwcap, hwcap2, &executed_ok_count, &sigill_count, &skipped_count);
    }
    out << "],";
    out << "\"summary\":{";
    out << "\"probe_count\":" << specs.size() << ",";
    out << "\"executed_ok_count\":" << executed_ok_count << ",";
    out << "\"sigill_count\":" << sigill_count << ",";
    out << "\"skipped_count\":" << skipped_count;
    out << "},";
    out << "\"warnings\":[";
    out << "\"Phase 7A executes tiny guarded CPU instruction probes only; not Qwen 9B inference\",";
    out << "\"SIGILL guard is a same-process safety net; process isolation remains future work for more destructive fuzzing\",";
    out << "\"ISA probe success only validates that one tiny instruction fixture executed, not full kernel correctness or performance\",";
    out << "\"not NPU, QNN, NNAPI, or Vulkan execution; not a performance target claim\"";
    out << "]";
    out << "}";
    return out.str();
}

}  // namespace

extern "C" JNIEXPORT jstring JNICALL
Java_com_qpnpu_trial_MainActivity_nativeRunPhase7AIsaProbes(JNIEnv* env, jobject /* thiz */) {
    const std::string json = RunPhase7AIsaProbesJson();
    return env->NewStringUTF(json.c_str());
}