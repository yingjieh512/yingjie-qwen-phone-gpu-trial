#include "qpnpu/kernels.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <sstream>
#include <string>
#include <vector>

namespace {

constexpr const char* kWarning = "local CPU microbenchmark; not a phone or NPU performance claim";

struct Options {
    std::string op{"int4_matvec"};
    std::size_t rows{256};
    std::size_t cols{256};
    std::size_t group_size{128};
    std::size_t n{4096};
    std::size_t iters{20};
    std::string out;
};

void usage(const char* argv0) {
    std::cout << "usage: " << argv0
              << " --operator int4_matvec|rmsnorm|rope|softmax [--rows N] [--cols N]"
              << " [--group-size N] [--n N] [--iters N] [--out PATH]\n";
}

bool parse_size(const std::string& text, std::size_t* value) {
    try {
        std::size_t consumed = 0;
        const unsigned long long parsed = std::stoull(text, &consumed);
        if (consumed != text.size()) {
            return false;
        }
        *value = static_cast<std::size_t>(parsed);
        return true;
    } catch (...) {
        return false;
    }
}

bool parse_args(int argc, char** argv, Options* options) {
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "-h" || arg == "--help") {
            usage(argv[0]);
            std::exit(0);
        }
        auto need_value = [&](const char* name) -> const char* {
            if (i + 1 >= argc) {
                std::cerr << "missing value for " << name << "\n";
                std::exit(2);
            }
            return argv[++i];
        };

        if (arg == "--operator") {
            options->op = need_value("--operator");
        } else if (arg == "--rows") {
            if (!parse_size(need_value("--rows"), &options->rows)) return false;
        } else if (arg == "--cols") {
            if (!parse_size(need_value("--cols"), &options->cols)) return false;
        } else if (arg == "--group-size") {
            if (!parse_size(need_value("--group-size"), &options->group_size)) return false;
        } else if (arg == "--n") {
            if (!parse_size(need_value("--n"), &options->n)) return false;
        } else if (arg == "--iters") {
            if (!parse_size(need_value("--iters"), &options->iters)) return false;
        } else if (arg == "--out") {
            options->out = need_value("--out");
        } else {
            std::cerr << "unknown argument: " << arg << "\n";
            return false;
        }
    }
    if (options->iters == 0) {
        options->iters = 1;
    }
    if (options->group_size == 0) {
        options->group_size = 1;
    }
    return true;
}

std::string utc_now_iso() {
    const std::time_t now = std::time(nullptr);
    std::tm tm{};
#if defined(_WIN32)
    gmtime_s(&tm, &now);
#else
    gmtime_r(&now, &tm);
#endif
    std::ostringstream oss;
    oss << std::put_time(&tm, "%Y-%m-%dT%H:%M:%SZ");
    return oss.str();
}

std::uint8_t encode_int4(int value) {
    return static_cast<std::uint8_t>(value) & 0x0F;
}

std::vector<std::uint8_t> pack_int4(const std::vector<int>& values) {
    std::vector<std::uint8_t> packed((values.size() + 1) / 2, 0);
    for (std::size_t i = 0; i < values.size(); ++i) {
        const std::uint8_t nibble = encode_int4(values[i]);
        if (i % 2 == 0) {
            packed[i / 2] |= nibble;
        } else {
            packed[i / 2] |= static_cast<std::uint8_t>(nibble << 4);
        }
    }
    return packed;
}

double percentile(std::vector<double> values, double q) {
    if (values.empty()) {
        return 0.0;
    }
    std::sort(values.begin(), values.end());
    const std::size_t index = static_cast<std::size_t>(q * static_cast<double>(values.size() - 1));
    return values[index];
}

template <typename Fn>
std::vector<double> measure(std::size_t iters, Fn&& fn, double* checksum) {
    for (int warmup = 0; warmup < 3; ++warmup) {
        *checksum += fn();
    }

    std::vector<double> latencies;
    latencies.reserve(iters);
    for (std::size_t i = 0; i < iters; ++i) {
        const auto start = std::chrono::steady_clock::now();
        *checksum += fn();
        const auto end = std::chrono::steady_clock::now();
        const std::chrono::duration<double, std::milli> elapsed = end - start;
        latencies.push_back(elapsed.count());
    }
    return latencies;
}

double run_int4_matvec(const Options& options, std::vector<double>* latencies) {
    std::mt19937 rng(1234);
    std::uniform_int_distribution<int> qdist(-8, 7);
    std::uniform_real_distribution<float> fdist(-1.0f, 1.0f);
    std::uniform_real_distribution<float> sdist(0.01f, 0.2f);

    const std::size_t groups = (options.cols + options.group_size - 1) / options.group_size;
    std::vector<int> qweights(options.rows * options.cols);
    for (int& value : qweights) {
        value = qdist(rng);
    }
    std::vector<std::uint8_t> packed = pack_int4(qweights);
    std::vector<float> scales(options.rows * groups);
    for (float& scale : scales) {
        scale = sdist(rng);
    }
    std::vector<float> input(options.cols);
    for (float& value : input) {
        value = fdist(rng);
    }
    std::vector<float> output(options.rows, 0.0f);

    double checksum = 0.0;
    auto body = [&]() -> double {
        qpnpu::int4_groupwise_matvec_ref(
            packed.data(), scales.data(), input.data(), output.data(),
            options.rows, options.cols, options.group_size);
        double sum = 0.0;
        for (float value : output) sum += value;
        return sum;
    };
    *latencies = measure(options.iters, body, &checksum);
    return checksum;
}

double run_rmsnorm(const Options& options, std::vector<double>* latencies) {
    std::mt19937 rng(1234);
    std::uniform_real_distribution<float> fdist(-1.0f, 1.0f);
    std::vector<float> x(options.n);
    std::vector<float> weight(options.n);
    std::vector<float> output(options.n);
    for (float& value : x) value = fdist(rng);
    for (float& value : weight) value = 0.5f + std::fabs(fdist(rng));

    double checksum = 0.0;
    auto body = [&]() -> double {
        qpnpu::rmsnorm_ref(x.data(), weight.data(), output.data(), options.n, 1e-5f);
        double sum = 0.0;
        for (float value : output) sum += value;
        return sum;
    };
    *latencies = measure(options.iters, body, &checksum);
    return checksum;
}

double run_rope(const Options& options, std::vector<double>* latencies) {
    std::mt19937 rng(1234);
    std::uniform_real_distribution<float> fdist(-1.0f, 1.0f);
    std::vector<float> x(options.n);
    std::vector<float> output(options.n);
    for (float& value : x) value = fdist(rng);

    double checksum = 0.0;
    auto body = [&]() -> double {
        qpnpu::rope_ref(x.data(), output.data(), options.n, 128, 10000.0f);
        double sum = 0.0;
        for (float value : output) sum += value;
        return sum;
    };
    *latencies = measure(options.iters, body, &checksum);
    return checksum;
}

double run_softmax(const Options& options, std::vector<double>* latencies) {
    std::mt19937 rng(1234);
    std::uniform_real_distribution<float> fdist(-10.0f, 10.0f);
    std::vector<float> logits(options.n);
    std::vector<float> output(options.n);
    for (float& value : logits) value = fdist(rng);

    double checksum = 0.0;
    auto body = [&]() -> double {
        qpnpu::softmax_ref(logits.data(), output.data(), options.n);
        double sum = 0.0;
        for (float value : output) sum += value;
        return sum;
    };
    *latencies = measure(options.iters, body, &checksum);
    return checksum;
}

std::string shape_json(const Options& options) {
    std::ostringstream oss;
    if (options.op == "int4_matvec") {
        oss << "{\n"
            << "    \"rows\": " << options.rows << ",\n"
            << "    \"cols\": " << options.cols << ",\n"
            << "    \"group_size\": " << options.group_size << "\n"
            << "  }";
    } else {
        oss << "{\n"
            << "    \"n\": " << options.n << "\n"
            << "  }";
    }
    return oss.str();
}

std::string benchmark_json(const Options& options, double p50, double p90, double p99) {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(6);
    oss << "{\n"
        << "  \"schema_version\": \"0.1\",\n"
        << "  \"timestamp_utc\": \"" << utc_now_iso() << "\",\n"
        << "  \"device\": {\"host\": \"local-development-machine\"},\n"
        << "  \"model\": {},\n"
        << "  \"backend\": \"cpu\",\n"
        << "  \"operator\": \"" << options.op << "\",\n"
        << "  \"shape\": " << shape_json(options) << ",\n"
        << "  \"metrics\": {\n"
        << "    \"latency_ms_p50\": " << p50 << ",\n"
        << "    \"latency_ms_p90\": " << p90 << ",\n"
        << "    \"latency_ms_p99\": " << p99 << ",\n"
        << "    \"tokens_per_second\": 0.0,\n"
        << "    \"memory_rss_mb\": 0.0\n"
        << "  },\n"
        << "  \"thermal\": {},\n"
        << "  \"kernel_config_hash\": \"local-cpu-ref\",\n"
        << "  \"warnings\": [\n"
        << "    \"" << kWarning << "\"\n"
        << "  ]\n"
        << "}\n";
    return oss.str();
}

bool write_text(const std::string& path_text, const std::string& content) {
    if (path_text.empty()) {
        return true;
    }
    const std::filesystem::path path(path_text);
    const auto parent = path.parent_path();
    if (!parent.empty()) {
        std::filesystem::create_directories(parent);
    }
    std::ofstream out(path, std::ios::binary);
    if (!out) {
        return false;
    }
    out << content;
    return true;
}

}  // namespace

int main(int argc, char** argv) {
    Options options;
    if (!parse_args(argc, argv, &options)) {
        usage(argv[0]);
        return 2;
    }

    std::vector<double> latencies;
    double checksum = 0.0;
    if (options.op == "int4_matvec") {
        checksum = run_int4_matvec(options, &latencies);
    } else if (options.op == "rmsnorm") {
        checksum = run_rmsnorm(options, &latencies);
    } else if (options.op == "rope") {
        checksum = run_rope(options, &latencies);
    } else if (options.op == "softmax") {
        checksum = run_softmax(options, &latencies);
    } else {
        std::cerr << "unsupported operator: " << options.op << "\n";
        return 2;
    }

    volatile double sink = checksum;
    (void)sink;

    const double p50 = percentile(latencies, 0.50);
    const double p90 = percentile(latencies, 0.90);
    const double p99 = percentile(latencies, 0.99);
    const std::string json = benchmark_json(options, p50, p90, p99);

    std::cout << "qpnpu local CPU microbenchmark\n";
    std::cout << "operator: " << options.op << "\n";
    std::cout << "iters: " << options.iters << "\n";
    std::cout << "latency_ms_p50: " << p50 << "\n";
    std::cout << "latency_ms_p90: " << p90 << "\n";
    std::cout << "latency_ms_p99: " << p99 << "\n";
    std::cout << "warning: " << kWarning << "\n";

    if (!options.out.empty()) {
        if (!write_text(options.out, json)) {
            std::cerr << "failed to write benchmark JSON: " << options.out << "\n";
            return 1;
        }
        std::cout << "wrote: " << options.out << "\n";
    }
    return 0;
}