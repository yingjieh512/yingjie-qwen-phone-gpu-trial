#include <jni.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <functional>
#include <iomanip>
#include <limits>
#include <numeric>
#include <sstream>
#include <string>
#include <vector>

namespace {

constexpr const char* kBackend = "cpu_android_native_reference";
constexpr const char* kKernelConfigHash = "phase5_native_reference_v1";
volatile float g_sink = 0.0f;

struct BenchStats {
    double p50_ms = 0.0;
    double p90_ms = 0.0;
    double p99_ms = 0.0;
    double throughput = 0.0;
};

struct BenchResult {
    std::string op;
    std::string shape_json;
    double max_abs_error = 0.0;
    bool passed = false;
    BenchStats stats;
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

BenchStats Measure(const std::function<void()>& fn, int iterations, double work_items) {
    std::vector<double> samples;
    samples.reserve(iterations);
    for (int i = 0; i < iterations; ++i) {
        const auto start = std::chrono::steady_clock::now();
        fn();
        const auto end = std::chrono::steady_clock::now();
        const double ms = std::chrono::duration<double, std::milli>(end - start).count();
        samples.push_back(ms);
    }
    std::sort(samples.begin(), samples.end());
    const auto percentile = [&](double p) {
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

float DeterministicValue(int index, float scale = 0.013f) {
    const int wrapped = (index * 37 + 17) % 97;
    return (static_cast<float>(wrapped) - 48.0f) * scale;
}

void Fp32MatvecKernel(const std::vector<float>& matrix, const std::vector<float>& vector,
                     std::vector<float>& output, int rows, int cols) {
    for (int r = 0; r < rows; ++r) {
        float acc = 0.0f;
        for (int c = 0; c < cols; ++c) {
            acc += matrix[r * cols + c] * vector[c];
        }
        output[r] = acc;
    }
}

BenchResult RunFp32Matvec() {
    constexpr int rows = 16;
    constexpr int cols = 32;
    std::vector<float> matrix(rows * cols);
    std::vector<float> vector(cols);
    std::vector<float> output(rows);
    std::vector<double> reference(rows);
    for (int i = 0; i < rows * cols; ++i) matrix[i] = DeterministicValue(i);
    for (int i = 0; i < cols; ++i) vector[i] = DeterministicValue(i + 100, 0.017f);
    for (int r = 0; r < rows; ++r) {
        double acc = 0.0;
        for (int c = 0; c < cols; ++c) acc += static_cast<double>(matrix[r * cols + c]) * vector[c];
        reference[r] = acc;
    }
    Fp32MatvecKernel(matrix, vector, output, rows, cols);
    double max_error = 0.0;
    for (int r = 0; r < rows; ++r) max_error = std::max(max_error, std::abs(static_cast<double>(output[r]) - reference[r]));
    auto stats = Measure([&]() {
        Fp32MatvecKernel(matrix, vector, output, rows, cols);
        g_sink += output[0] * 1.0e-12f;
    }, 300, static_cast<double>(rows));
    return {"fp32_matvec", "{\"rows\":16,\"cols\":32}", max_error, max_error < 1.0e-4, stats};
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

BenchResult RunInt4DequantMatvec() {
    constexpr int rows = 16;
    constexpr int cols = 32;
    std::vector<int> q(rows * cols);
    std::vector<uint8_t> packed((rows * cols + 1) / 2);
    std::vector<float> scales(rows);
    std::vector<float> vector(cols);
    std::vector<float> output(rows);
    std::vector<double> reference(rows);
    for (int i = 0; i < rows * cols; ++i) q[i] = ((i * 5 + 3) % 16) - 8;
    for (int i = 0; i < rows * cols; i += 2) packed[i / 2] = PackInt4Pair(q[i], q[i + 1]);
    for (int r = 0; r < rows; ++r) scales[r] = 0.01f + static_cast<float>(r) * 0.001f;
    for (int i = 0; i < cols; ++i) vector[i] = DeterministicValue(i + 200, 0.011f);
    for (int r = 0; r < rows; ++r) {
        double acc = 0.0;
        for (int c = 0; c < cols; ++c) acc += static_cast<double>(q[r * cols + c]) * scales[r] * vector[c];
        reference[r] = acc;
    }
    Int4DequantMatvecKernel(packed, scales, vector, output, rows, cols);
    double max_error = 0.0;
    for (int r = 0; r < rows; ++r) max_error = std::max(max_error, std::abs(static_cast<double>(output[r]) - reference[r]));
    auto stats = Measure([&]() {
        Int4DequantMatvecKernel(packed, scales, vector, output, rows, cols);
        g_sink += output[0] * 1.0e-12f;
    }, 300, static_cast<double>(rows));
    return {"int4_dequant_matvec", "{\"rows\":16,\"cols\":32,\"group_size\":32}", max_error, max_error < 1.0e-4, stats};
}

void RmsNormKernel(const std::vector<float>& input, const std::vector<float>& weight,
                   std::vector<float>& output, float eps) {
    float ss = 0.0f;
    for (float v : input) ss += v * v;
    const float inv = 1.0f / std::sqrt(ss / static_cast<float>(input.size()) + eps);
    for (size_t i = 0; i < input.size(); ++i) output[i] = input[i] * inv * weight[i];
}

BenchResult RunRmsNorm() {
    constexpr int n = 64;
    std::vector<float> input(n), weight(n), output(n);
    std::vector<double> reference(n);
    for (int i = 0; i < n; ++i) {
        input[i] = DeterministicValue(i + 300, 0.019f);
        weight[i] = 0.9f + static_cast<float>(i) * 0.002f;
    }
    double ss = 0.0;
    for (float v : input) ss += static_cast<double>(v) * v;
    const double inv = 1.0 / std::sqrt(ss / n + 1.0e-6);
    for (int i = 0; i < n; ++i) reference[i] = input[i] * inv * weight[i];
    RmsNormKernel(input, weight, output, 1.0e-6f);
    double max_error = 0.0;
    for (int i = 0; i < n; ++i) max_error = std::max(max_error, std::abs(static_cast<double>(output[i]) - reference[i]));
    auto stats = Measure([&]() {
        RmsNormKernel(input, weight, output, 1.0e-6f);
        g_sink += output[0] * 1.0e-12f;
    }, 500, static_cast<double>(n));
    return {"rmsnorm", "{\"n\":64}", max_error, max_error < 1.0e-4, stats};
}

void SoftmaxKernel(const std::vector<float>& input, std::vector<float>& output) {
    const float max_v = *std::max_element(input.begin(), input.end());
    float sum = 0.0f;
    for (size_t i = 0; i < input.size(); ++i) {
        output[i] = std::exp(input[i] - max_v);
        sum += output[i];
    }
    for (float& v : output) v /= sum;
}

BenchResult RunSoftmax() {
    constexpr int n = 64;
    std::vector<float> input(n), output(n);
    std::vector<double> reference(n);
    for (int i = 0; i < n; ++i) input[i] = DeterministicValue(i + 400, 0.031f);
    const auto max_it = std::max_element(input.begin(), input.end());
    double sum = 0.0;
    for (int i = 0; i < n; ++i) {
        reference[i] = std::exp(static_cast<double>(input[i] - *max_it));
        sum += reference[i];
    }
    for (double& v : reference) v /= sum;
    SoftmaxKernel(input, output);
    double max_error = 0.0;
    for (int i = 0; i < n; ++i) max_error = std::max(max_error, std::abs(static_cast<double>(output[i]) - reference[i]));
    auto stats = Measure([&]() {
        SoftmaxKernel(input, output);
        g_sink += output[0] * 1.0e-12f;
    }, 500, static_cast<double>(n));
    return {"softmax", "{\"n\":64}", max_error, max_error < 1.0e-6, stats};
}

void RopeKernel(const std::vector<float>& input, std::vector<float>& output, int position, float theta) {
    const int half = static_cast<int>(input.size()) / 2;
    for (int i = 0; i < half; ++i) {
        const float freq = std::pow(theta, -2.0f * static_cast<float>(i) / static_cast<float>(input.size()));
        const float angle = static_cast<float>(position) * freq;
        const float c = std::cos(angle);
        const float s = std::sin(angle);
        const float x0 = input[2 * i];
        const float x1 = input[2 * i + 1];
        output[2 * i] = x0 * c - x1 * s;
        output[2 * i + 1] = x0 * s + x1 * c;
    }
}

BenchResult RunRope() {
    constexpr int n = 64;
    std::vector<float> input(n), output(n);
    std::vector<double> reference(n);
    for (int i = 0; i < n; ++i) input[i] = DeterministicValue(i + 500, 0.021f);
    for (int i = 0; i < n / 2; ++i) {
        const double freq = std::pow(10000.0, -2.0 * static_cast<double>(i) / n);
        const double angle = 7.0 * freq;
        const double c = std::cos(angle);
        const double s = std::sin(angle);
        reference[2 * i] = input[2 * i] * c - input[2 * i + 1] * s;
        reference[2 * i + 1] = input[2 * i] * s + input[2 * i + 1] * c;
    }
    RopeKernel(input, output, 7, 10000.0f);
    double max_error = 0.0;
    for (int i = 0; i < n; ++i) max_error = std::max(max_error, std::abs(static_cast<double>(output[i]) - reference[i]));
    auto stats = Measure([&]() {
        RopeKernel(input, output, 7, 10000.0f);
        g_sink += output[0] * 1.0e-12f;
    }, 500, static_cast<double>(n));
    return {"rope", "{\"n\":64,\"position\":7,\"rope_theta\":10000.0}", max_error, max_error < 1.0e-4, stats};
}

std::string BenchmarkResultJson(const BenchResult& result) {
    std::ostringstream out;
    out << std::fixed << std::setprecision(6);
    out << "{";
    out << "\"schema_version\":\"0.1\",";
    out << "\"timestamp_utc\":\"native_clock_unavailable\",";
    out << "\"device\":{\"type\":\"android_device\"},";
    out << "\"model\":{\"architecture\":\"native_microfixture\",\"hf_id\":\"local/native-microbench\"},";
    out << "\"backend\":\"" << kBackend << "\",";
    out << "\"operator\":\"" << JsonEscape(result.op) << "\",";
    out << "\"shape\":" << result.shape_json << ",";
    out << "\"metrics\":{";
    out << "\"latency_ms_p50\":" << result.stats.p50_ms << ",";
    out << "\"latency_ms_p90\":" << result.stats.p90_ms << ",";
    out << "\"latency_ms_p99\":" << result.stats.p99_ms << ",";
    out << "\"tokens_per_second\":0.0,";
    out << "\"memory_rss_mb\":0.0,";
    out << "\"native_work_items_per_second\":" << result.stats.throughput << ",";
    out << "\"max_abs_error\":" << result.max_abs_error << ",";
    out << "\"correctness_passed\":" << (result.passed ? "true" : "false");
    out << "},";
    out << "\"thermal\":{},";
    out << "\"kernel_config_hash\":\"" << kKernelConfigHash << "\",";
    out << "\"warnings\":[\"tiny native CPU microbenchmark; not Qwen 9B, not Android NPU, not a performance claim\"]";
    out << "}";
    return out.str();
}

std::string RunAllBenchmarksJson() {
    const std::vector<BenchResult> results = {
            RunFp32Matvec(),
            RunInt4DequantMatvec(),
            RunRmsNorm(),
            RunSoftmax(),
            RunRope(),
    };
    bool all_passed = true;
    for (const auto& result : results) all_passed = all_passed && result.passed;

    std::ostringstream out;
    out << "{";
    out << "\"schema_version\":\"0.1\",";
    out << "\"source\":\"android-native-microbench\",";
    out << "\"backend\":\"" << kBackend << "\",";
    out << "\"native_library\":\"qpnpu_probe_native\",";
    out << "\"all_correctness_passed\":" << (all_passed ? "true" : "false") << ",";
    out << "\"results\":[";
    for (size_t i = 0; i < results.size(); ++i) {
        if (i) out << ",";
        out << BenchmarkResultJson(results[i]);
    }
    out << "],";
    out << "\"warnings\":[";
    out << "\"tiny deterministic native CPU microbenchmarks only\",";
    out << "\"not Qwen 9B inference\",";
    out << "\"not NPU or QNN execution\",";
    out << "\"not a performance target claim\"";
    out << "]";
    out << "}";
    return out.str();
}

}  // namespace

extern "C" JNIEXPORT jstring JNICALL
Java_com_qpnpu_trial_MainActivity_nativeRunMicrobenchmarks(JNIEnv* env, jobject /* thiz */) {
    const std::string json = RunAllBenchmarksJson();
    return env->NewStringUTF(json.c_str());
}