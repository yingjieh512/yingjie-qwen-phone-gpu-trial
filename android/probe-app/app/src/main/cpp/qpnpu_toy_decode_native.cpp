#include <jni.h>

#include <algorithm>
#include <chrono>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr const char* kBackend = "cpu_android_native_reference";
constexpr float kRmsEps = 1.0e-6f;

std::string JsonEscape(const std::string& value) {
    std::ostringstream out;
    for (unsigned char ch : value) {
        switch (ch) {
            case '\\': out << "\\\\"; break;
            case '"': out << "\\\""; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default:
                if (ch < 0x20) {
                    out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << static_cast<int>(ch)
                        << std::dec << std::setfill(' ');
                } else if (ch < 0x7f) {
                    out << static_cast<char>(ch);
                } else {
                    out << "\\x" << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(ch)
                        << std::dec << std::setfill(' ');
                }
        }
    }
    return out.str();
}

int FindJsonInt(const std::string& json, const std::string& key) {
    const std::string needle = "\"" + key + "\"";
    size_t pos = json.find(needle);
    if (pos == std::string::npos) {
        throw std::runtime_error("missing metadata integer key: " + key);
    }
    pos = json.find(':', pos + needle.size());
    if (pos == std::string::npos) {
        throw std::runtime_error("malformed metadata integer key: " + key);
    }
    ++pos;
    while (pos < json.size() && std::isspace(static_cast<unsigned char>(json[pos]))) {
        ++pos;
    }
    size_t end = pos;
    while (end < json.size() && (std::isdigit(static_cast<unsigned char>(json[end])) || json[end] == '-')) {
        ++end;
    }
    if (end == pos) {
        throw std::runtime_error("metadata key is not an integer: " + key);
    }
    return std::stoi(json.substr(pos, end - pos));
}

std::string FindJsonString(const std::string& json, const std::string& key, const std::string& fallback) {
    const std::string needle = "\"" + key + "\"";
    size_t pos = json.find(needle);
    if (pos == std::string::npos) {
        return fallback;
    }
    pos = json.find(':', pos + needle.size());
    if (pos == std::string::npos) {
        return fallback;
    }
    pos = json.find('"', pos);
    if (pos == std::string::npos) {
        return fallback;
    }
    const size_t start = pos + 1;
    size_t end = start;
    while (end < json.size()) {
        if (json[end] == '"' && json[end - 1] != '\\') {
            return json.substr(start, end - start);
        }
        ++end;
    }
    return fallback;
}

std::string ExtractModelObject(const std::string& metadata_json) {
    const std::string needle = "\"model\"";
    size_t pos = metadata_json.find(needle);
    if (pos == std::string::npos) {
        return metadata_json;
    }
    pos = metadata_json.find('{', pos + needle.size());
    if (pos == std::string::npos) {
        return metadata_json;
    }
    int depth = 0;
    for (size_t i = pos; i < metadata_json.size(); ++i) {
        if (metadata_json[i] == '{') {
            ++depth;
        } else if (metadata_json[i] == '}') {
            --depth;
            if (depth == 0) {
                return metadata_json.substr(pos, i - pos + 1);
            }
        }
    }
    return metadata_json;
}

std::vector<float> FloatsFromBytes(const std::vector<uint8_t>& bytes) {
    if (bytes.size() % sizeof(float) != 0) {
        throw std::runtime_error("model.bin length is not divisible by fp32 size");
    }
    std::vector<float> values(bytes.size() / sizeof(float));
    std::memcpy(values.data(), bytes.data(), bytes.size());
    return values;
}

std::vector<int> EncodePrompt(const std::string& prompt, int vocab_size) {
    std::vector<int> ids;
    ids.reserve(prompt.size());
    for (unsigned char ch : prompt) {
        ids.push_back(static_cast<int>(ch) % vocab_size);
    }
    if (ids.empty()) {
        ids.push_back(0);
    }
    return ids;
}

std::string TokenIdsJson(const std::vector<int>& ids) {
    std::ostringstream out;
    out << "[";
    for (size_t i = 0; i < ids.size(); ++i) {
        if (i) out << ",";
        out << ids[i];
    }
    out << "]";
    return out.str();
}

std::string DecodeGeneratedText(const std::vector<int>& ids) {
    std::ostringstream out;
    for (int id : ids) {
        const int byte = id & 0xff;
        if (byte >= 32 && byte <= 126) {
            out << static_cast<char>(byte);
        } else {
            out << "\\x" << std::hex << std::setw(2) << std::setfill('0') << byte << std::dec << std::setfill(' ');
        }
    }
    return out.str();
}

int ArgmaxNextToken(const std::vector<float>& tensors, int vocab_size, int hidden_size,
                    int token_id, int position) {
    const size_t embedding_offset = 0;
    const size_t norm_offset = static_cast<size_t>(vocab_size) * hidden_size;
    const size_t lm_head_offset = norm_offset + hidden_size;

    std::vector<float> hidden(static_cast<size_t>(hidden_size));
    double sum_sq = 0.0;
    for (int h = 0; h < hidden_size; ++h) {
        const float value = tensors[embedding_offset + static_cast<size_t>(token_id) * hidden_size + h];
        hidden[static_cast<size_t>(h)] = value;
        sum_sq += static_cast<double>(value) * value;
    }
    const float inv_rms = 1.0f / std::sqrt(static_cast<float>(sum_sq / hidden_size) + kRmsEps);
    for (int h = 0; h < hidden_size; ++h) {
        hidden[static_cast<size_t>(h)] = hidden[static_cast<size_t>(h)] * inv_rms * tensors[norm_offset + h];
    }
    hidden[static_cast<size_t>((position + token_id) % hidden_size)] += 0.001f * static_cast<float>(position + 1);

    int best_token = 0;
    float best_logit = -std::numeric_limits<float>::infinity();
    for (int v = 0; v < vocab_size; ++v) {
        float logit = 0.0f;
        const size_t row = lm_head_offset + static_cast<size_t>(v) * hidden_size;
        for (int h = 0; h < hidden_size; ++h) {
            logit += tensors[row + h] * hidden[static_cast<size_t>(h)];
        }
        if (logit > best_logit) {
            best_logit = logit;
            best_token = v;
        }
    }
    return best_token;
}

std::string RunToyDecodeJson(const std::string& metadata_json, const std::vector<uint8_t>& model_bytes,
                             const std::string& prompt, int max_new_tokens) {
    if (max_new_tokens < 0 || max_new_tokens > 128) {
        throw std::runtime_error("max_new_tokens must be in range 0..128");
    }
    const std::string model_json = ExtractModelObject(metadata_json);
    const int vocab_size = FindJsonInt(model_json, "vocab_size");
    const int hidden_size = FindJsonInt(model_json, "hidden_size");
    const int num_layers = FindJsonInt(model_json, "num_layers");
    const std::string architecture = FindJsonString(model_json, "architecture", "qwen_toy");
    const std::string hf_id = FindJsonString(model_json, "hf_id", "local/toy-qwen-smoke");
    if (architecture != "qwen_toy") {
        throw std::runtime_error("expected qwen_toy architecture in asset metadata");
    }
    if (vocab_size <= 0 || vocab_size > 256 || hidden_size <= 0 || hidden_size > 1024) {
        throw std::runtime_error("toy metadata has unsupported vocab or hidden size");
    }
    const size_t expected_floats = static_cast<size_t>(vocab_size) * hidden_size * 2u + hidden_size;
    if (model_bytes.size() != expected_floats * sizeof(float)) {
        throw std::runtime_error("model.bin length does not match expected toy tensor layout");
    }

    const std::vector<float> tensors = FloatsFromBytes(model_bytes);
    std::vector<int> prompt_ids = EncodePrompt(prompt, vocab_size);
    std::vector<int> generated_ids;
    generated_ids.reserve(static_cast<size_t>(max_new_tokens));

    int current = prompt_ids.back();
    const auto start = std::chrono::steady_clock::now();
    for (int pos = 0; pos < max_new_tokens; ++pos) {
        const int next = ArgmaxNextToken(tensors, vocab_size, hidden_size, current, pos);
        generated_ids.push_back(next);
        current = next;
    }
    const auto end = std::chrono::steady_clock::now();
    const double latency_ms = std::chrono::duration<double, std::milli>(end - start).count();
    const double tokens_per_second = latency_ms > 0.0
            ? (static_cast<double>(generated_ids.size()) * 1000.0 / latency_ms)
            : 0.0;

    std::ostringstream out;
    out << std::fixed << std::setprecision(6);
    out << "{";
    out << "\"schema_version\":\"0.1\",";
    out << "\"source\":\"android-toy-decode\",";
    out << "\"backend\":\"" << kBackend << "\",";
    out << "\"native_library\":\"qpnpu_probe_native\",";
    out << "\"model\":{";
    out << "\"architecture\":\"" << JsonEscape(architecture) << "\",";
    out << "\"hf_id\":\"" << JsonEscape(hf_id) << "\",";
    out << "\"hidden_size\":" << hidden_size << ",";
    out << "\"num_layers\":" << num_layers << ",";
    out << "\"vocab_size\":" << vocab_size << "},";
    out << "\"asset_model\":{";
    out << "\"metadata_asset\":\"toy_qwen_7b/metadata.json\",";
    out << "\"tensor_asset\":\"toy_qwen_7b/model.bin\",";
    out << "\"tensor_bytes\":" << model_bytes.size() << "},";
    out << "\"tokenizer\":{\"type\":\"byte_tokenizer_stub\",\"is_qwen_tokenizer\":false},";
    out << "\"prompt\":\"" << JsonEscape(prompt) << "\",";
    out << "\"prompt_token_ids\":" << TokenIdsJson(prompt_ids) << ",";
    out << "\"generated_token_ids\":" << TokenIdsJson(generated_ids) << ",";
    out << "\"generated_text\":\"" << JsonEscape(DecodeGeneratedText(generated_ids)) << "\",";
    out << "\"decode\":{";
    out << "\"max_new_tokens\":" << max_new_tokens << ",";
    out << "\"latency_ms_total\":" << latency_ms << ",";
    out << "\"tokens_per_second\":" << tokens_per_second << "},";
    out << "\"benchmark\":{";
    out << "\"schema_version\":\"0.1\",";
    out << "\"timestamp_utc\":\"native_clock_unavailable\",";
    out << "\"device\":{\"type\":\"android_device\"},";
    out << "\"model\":{\"architecture\":\"qwen_toy\",\"hf_id\":\"" << JsonEscape(hf_id) << "\"},";
    out << "\"backend\":\"" << kBackend << "\",";
    out << "\"operator\":\"toy_decode\",";
    out << "\"shape\":{\"max_new_tokens\":" << max_new_tokens
        << ",\"hidden_size\":" << hidden_size << ",\"vocab_size\":" << vocab_size << "},";
    out << "\"metrics\":{\"latency_ms_p50\":" << latency_ms
        << ",\"latency_ms_p90\":" << latency_ms
        << ",\"latency_ms_p99\":" << latency_ms
        << ",\"tokens_per_second\":" << tokens_per_second
        << ",\"memory_rss_mb\":0.0},";
    out << "\"thermal\":{},";
    out << "\"kernel_config_hash\":\"toy_android_asset_v1\",";
    out << "\"warnings\":[\"toy Android CPU/JNI decode only; not Qwen 9B; not NPU; not a performance claim\"]";
    out << "},";
    out << "\"warnings\":[";
    out << "\"toy model only; not Qwen 9B\",";
    out << "\"Android CPU/JNI reference only; not NPU, QNN, NNAPI, or Vulkan execution\",";
    out << "\"byte tokenizer stub only; not the Qwen tokenizer\",";
    out << "\"not a performance target claim\"";
    out << "]";
    out << "}";
    return out.str();
}

std::string JStringToStdString(JNIEnv* env, jstring value) {
    if (value == nullptr) {
        return "";
    }
    const char* chars = env->GetStringUTFChars(value, nullptr);
    if (chars == nullptr) {
        return "";
    }
    std::string result(chars);
    env->ReleaseStringUTFChars(value, chars);
    return result;
}

std::vector<uint8_t> JByteArrayToVector(JNIEnv* env, jbyteArray array) {
    if (array == nullptr) {
        return {};
    }
    const jsize length = env->GetArrayLength(array);
    std::vector<uint8_t> bytes(static_cast<size_t>(length));
    if (length > 0) {
        env->GetByteArrayRegion(array, 0, length, reinterpret_cast<jbyte*>(bytes.data()));
    }
    return bytes;
}

}  // namespace

extern "C" JNIEXPORT jstring JNICALL
Java_com_qpnpu_trial_MainActivity_nativeRunToyDecode(JNIEnv* env, jobject /* thiz */,
                                                     jstring metadata_json,
                                                     jbyteArray model_bytes,
                                                     jstring prompt,
                                                     jint max_new_tokens) {
    try {
        const std::string metadata = JStringToStdString(env, metadata_json);
        const std::vector<uint8_t> bytes = JByteArrayToVector(env, model_bytes);
        const std::string prompt_text = JStringToStdString(env, prompt);
        const std::string json = RunToyDecodeJson(metadata, bytes, prompt_text, static_cast<int>(max_new_tokens));
        return env->NewStringUTF(json.c_str());
    } catch (const std::exception& exc) {
        const std::string message = std::string("nativeRunToyDecode failed: ") + exc.what();
        jclass runtime_exception = env->FindClass("java/lang/RuntimeException");
        if (runtime_exception != nullptr) {
            env->ThrowNew(runtime_exception, message.c_str());
        }
        return env->NewStringUTF("{}");
    }
}