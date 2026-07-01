package com.qpnpu.trial;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.graphics.Typeface;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Arrays;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;
import java.util.concurrent.TimeUnit;

public class MainActivity extends Activity {
    private static final String TAG = "QPNPUProbe";
    private static final String JSON_BEGIN = "QPNPU_PROBE_JSON_BEGIN";
    private static final String JSON_END = "QPNPU_PROBE_JSON_END";
    private static final String NATIVE_JSON_BEGIN = "QPNPU_NATIVE_BENCH_JSON_BEGIN";
    private static final String NATIVE_JSON_END = "QPNPU_NATIVE_BENCH_JSON_END";
    private static final String PHASE6_JSON_BEGIN = "QPNPU_PHASE6_JSON_BEGIN";
    private static final String PHASE6_JSON_END = "QPNPU_PHASE6_JSON_END";
    private static final String PHASE7A_JSON_BEGIN = "QPNPU_PHASE7A_JSON_BEGIN";
    private static final String PHASE7A_JSON_END = "QPNPU_PHASE7A_JSON_END";
    private static final int LOG_CHUNK_SIZE = 3000;
    private static boolean nativeLibraryLoaded = false;
    private static String nativeLibraryLoadError = "";

    static {
        try {
            System.loadLibrary("qpnpu_probe_native");
            nativeLibraryLoaded = true;
        } catch (UnsatisfiedLinkError exc) {
            nativeLibraryLoadError = exc.toString();
        }
    }

    private TextView outputText;
    private String lastJson = "";

    private native String nativeRunMicrobenchmarks();
    private native String nativeRunPhase6Characterization();
    private native String nativeRunPhase7AIsaProbes();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setTitle("QPNPU Hardware Probe");

        int pad = dp(12);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(pad, pad, pad, pad);

        TextView title = new TextView(this);
        title.setText("QPNPU Hardware Probe");
        title.setTextSize(22);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        root.addView(title, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT));

        LinearLayout primaryButtons = new LinearLayout(this);
        primaryButtons.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout characterizationButtons = new LinearLayout(this);
        characterizationButtons.setOrientation(LinearLayout.HORIZONTAL);

        Button runButton = new Button(this);
        runButton.setText("Run Probe");
        Button nativeButton = new Button(this);
        nativeButton.setText("Native Bench");
        Button phase6Button = new Button(this);
        phase6Button.setText("Characterize HW");
        Button isaButton = new Button(this);
        isaButton.setText("ISA Probe");
        Button copyButton = new Button(this);
        copyButton.setText("Copy JSON");
        Button clearButton = new Button(this);
        clearButton.setText("Clear");

        LinearLayout.LayoutParams buttonParams = new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1.0f);
        primaryButtons.addView(runButton, buttonParams);
        primaryButtons.addView(nativeButton, buttonParams);
        root.addView(primaryButtons, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT));

        characterizationButtons.addView(phase6Button, buttonParams);
        characterizationButtons.addView(isaButton, buttonParams);
        root.addView(characterizationButtons, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT));

        LinearLayout utilityButtons = new LinearLayout(this);
        utilityButtons.setOrientation(LinearLayout.HORIZONTAL);
        utilityButtons.addView(copyButton, buttonParams);
        utilityButtons.addView(clearButton, buttonParams);
        root.addView(utilityButtons, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT));

        outputText = new TextView(this);
        outputText.setTypeface(Typeface.MONOSPACE);
        outputText.setTextIsSelectable(true);
        outputText.setText("Tap Run Probe, Native Bench, Characterize HW, or ISA Probe for hardware evidence.");

        ScrollView scrollView = new ScrollView(this);
        scrollView.addView(outputText, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT,
                ScrollView.LayoutParams.WRAP_CONTENT));
        root.addView(scrollView, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1.0f));

        setContentView(root);

        runButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                runProbe();
            }
        });
        nativeButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                runNativeBench();
            }
        });
        phase6Button.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                runPhase6Characterization();
            }
        });
        isaButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                runPhase7AIsaProbe();
            }
        });
        copyButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                copyLastJson();
            }
        });
        clearButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                lastJson = "";
                outputText.setText("");
            }
        });
    }

    private void runProbe() {
        outputText.setText("Running probe...");
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    JSONObject probe = buildProbeJson();
                    String json = saveAndFinalizeJson(probe);
                    lastJson = json;
                    logProbeJson(json);
                    showText(json);
                } catch (final Exception exc) {
                    final String message = "Probe failed without crashing the app:\n" + exc;
                    Log.e(TAG, message, exc);
                    showText(message);
                }
            }
        }).start();
    }

    private void runNativeBench() {
        outputText.setText("Running native microbenchmarks...");
        new Thread(new Runnable() {
            @Override
            public void run() {
                JSONArray warnings = new JSONArray();
                try {
                    JSONObject nativeJson = collectNativeMicrobenchmarks(warnings);
                    nativeJson.put("timestamp_utc", utcNow());
                    nativeJson.put("device", collectDeviceInfo(warnings));
                    nativeJson.put("thermal", collectThermalHints(warnings));
                    nativeJson.put("warnings_from_java", warnings);
                    saveJsonToExternalFile(nativeJson, "native_microbenchmarks.json", warnings);
                    lastJson = nativeJson.toString(2);
                    logNativeBenchmarkJson(lastJson);
                    showText(lastJson);
                } catch (final Exception exc) {
                    final String message = "Native microbenchmark failed without crashing the app:\n" + exc;
                    Log.e(TAG, message, exc);
                    showText(message);
                }
            }
        }).start();
    }


    private void runPhase6Characterization() {
        outputText.setText("Running hardware characterization...");
        new Thread(new Runnable() {
            @Override
            public void run() {
                JSONArray warnings = new JSONArray();
                try {
                    JSONObject phase6Json = collectPhase6Characterization(warnings);
                    phase6Json.put("timestamp_utc", utcNow());
                    phase6Json.put("device", collectDeviceInfo(warnings));
                    phase6Json.put("thermal", collectThermalHints(warnings));
                    phase6Json.put("warnings_from_java", warnings);
                    saveJsonToExternalFile(phase6Json, "phase6_characterization.json", warnings);
                    lastJson = phase6Json.toString(2);
                    logPhase6Json(lastJson);
                    showText(lastJson);
                } catch (final Exception exc) {
                    final String message = "Hardware characterization failed without crashing the app:\n" + exc;
                    Log.e(TAG, message, exc);
                    showText(message);
                }
            }
        }).start();
    }

    private void runPhase7AIsaProbe() {
        outputText.setText("Running guarded ISA probes...");
        new Thread(new Runnable() {
            @Override
            public void run() {
                JSONArray warnings = new JSONArray();
                try {
                    JSONObject isaJson = collectPhase7AIsaProbes(warnings);
                    isaJson.put("timestamp_utc", utcNow());
                    isaJson.put("device", collectDeviceInfo(warnings));
                    isaJson.put("thermal", collectThermalHints(warnings));
                    isaJson.put("warnings_from_java", warnings);
                    saveJsonToExternalFile(isaJson, "phase7a_isa_probes.json", warnings);
                    lastJson = isaJson.toString(2);
                    logPhase7AJson(lastJson);
                    showText(lastJson);
                } catch (final Exception exc) {
                    final String message = "Guarded ISA probe failed without crashing the app:\n" + exc;
                    Log.e(TAG, message, exc);
                    showText(message);
                }
            }
        }).start();
    }
    private void copyLastJson() {
        if (lastJson.isEmpty()) {
            Toast.makeText(this, "No JSON to copy yet", Toast.LENGTH_SHORT).show();
            return;
        }
        ClipboardManager clipboard = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        if (clipboard != null) {
            clipboard.setPrimaryClip(ClipData.newPlainText("QPNPU probe JSON", lastJson));
            Toast.makeText(this, "Copied QPNPU JSON", Toast.LENGTH_SHORT).show();
        }
    }

    private void showText(final String text) {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                outputText.setText(text);
            }
        });
    }

    private JSONObject buildProbeJson() throws JSONException {
        JSONArray warnings = new JSONArray();
        JSONObject root = new JSONObject();
        root.put("schema_version", "0.1");
        root.put("timestamp_utc", utcNow());
        root.put("source", "android-probe-app");
        root.put("device", collectDeviceInfo(warnings));
        root.put("cpu", collectCpuInfo(warnings));
        root.put("memory", collectMemInfo(warnings));
        root.put("gpu", collectGpuHints(warnings));
        root.put("npu", collectNpuHints(warnings));
        root.put("thermal", collectThermalHints(warnings));
        root.put("microbenchmarks", collectNativeMicrobenchmarks(warnings));
        root.put("summary", buildCapabilitySummary(root));
        root.put("warnings", warnings);
        return root;
    }


    private JSONObject collectPhase6Characterization(JSONArray warnings) throws JSONException {
        if (!nativeLibraryLoaded) {
            JSONObject unavailable = new JSONObject();
            unavailable.put("schema_version", "0.1");
            unavailable.put("source", "android-phase6-characterization");
            unavailable.put("timestamp_utc", utcNow());
            unavailable.put("backend", "cpu_android_native_reference");
            unavailable.put("available", false);
            unavailable.put("native_library", "qpnpu_probe_native");
            unavailable.put("error", nativeLibraryLoadError);
            unavailable.put("warnings", new JSONArray().put("native library was not loaded; Phase 6 characterization did not run"));
            warnings.put("Phase 6 native library was not loaded: " + nativeLibraryLoadError);
            return unavailable;
        }

        try {
            JSONObject payload = new JSONObject(nativeRunPhase6Characterization());
            payload.put("timestamp_utc", utcNow());
            payload.put("available", true);
            return payload;
        } catch (Throwable exc) {
            JSONObject failed = new JSONObject();
            failed.put("schema_version", "0.1");
            failed.put("source", "android-phase6-characterization");
            failed.put("timestamp_utc", utcNow());
            failed.put("backend", "cpu_android_native_reference");
            failed.put("available", false);
            failed.put("native_library", "qpnpu_probe_native");
            failed.put("error", exc.toString());
            failed.put("warnings", new JSONArray().put("Phase 6 characterization failed; no accelerator performance claim"));
            warnings.put("Phase 6 characterization failed: " + exc);
            return failed;
        }
    }

    private JSONObject collectPhase7AIsaProbes(JSONArray warnings) throws JSONException {
        if (!nativeLibraryLoaded) {
            JSONObject unavailable = new JSONObject();
            unavailable.put("schema_version", "0.1");
            unavailable.put("source", "android-phase7a-isa-probes");
            unavailable.put("timestamp_utc", utcNow());
            unavailable.put("backend", "cpu_android_native_reference");
            unavailable.put("available", false);
            unavailable.put("native_library", "qpnpu_probe_native");
            unavailable.put("error", nativeLibraryLoadError);
            unavailable.put("isa_probes", new JSONArray());
            unavailable.put("warnings", new JSONArray().put("native library was not loaded; Phase 7A ISA probes did not run"));
            warnings.put("Phase 7A native library was not loaded: " + nativeLibraryLoadError);
            return unavailable;
        }

        try {
            JSONObject payload = new JSONObject(nativeRunPhase7AIsaProbes());
            payload.put("timestamp_utc", utcNow());
            payload.put("available", true);
            return payload;
        } catch (Throwable exc) {
            JSONObject failed = new JSONObject();
            failed.put("schema_version", "0.1");
            failed.put("source", "android-phase7a-isa-probes");
            failed.put("timestamp_utc", utcNow());
            failed.put("backend", "cpu_android_native_reference");
            failed.put("available", false);
            failed.put("native_library", "qpnpu_probe_native");
            failed.put("error", exc.toString());
            failed.put("isa_probes", new JSONArray());
            failed.put("warnings", new JSONArray().put("Phase 7A guarded ISA probes failed; no performance claim"));
            warnings.put("Phase 7A guarded ISA probes failed: " + exc);
            return failed;
        }
    }
    private JSONObject collectNativeMicrobenchmarks(JSONArray warnings) throws JSONException {
        if (!nativeLibraryLoaded) {
            JSONObject unavailable = new JSONObject();
            unavailable.put("schema_version", "0.1");
            unavailable.put("source", "android-native-microbench");
            unavailable.put("timestamp_utc", utcNow());
            unavailable.put("backend", "cpu_android_native_reference");
            unavailable.put("available", false);
            unavailable.put("native_library", "qpnpu_probe_native");
            unavailable.put("error", nativeLibraryLoadError);
            unavailable.put("results", new JSONArray());
            unavailable.put("warnings", new JSONArray().put("native library was not loaded; no native microbenchmarks ran"));
            warnings.put("native microbenchmark library was not loaded: " + nativeLibraryLoadError);
            return unavailable;
        }

        try {
            JSONObject payload = new JSONObject(nativeRunMicrobenchmarks());
            payload.put("timestamp_utc", utcNow());
            payload.put("available", true);
            return payload;
        } catch (Throwable exc) {
            JSONObject failed = new JSONObject();
            failed.put("schema_version", "0.1");
            failed.put("source", "android-native-microbench");
            failed.put("timestamp_utc", utcNow());
            failed.put("backend", "cpu_android_native_reference");
            failed.put("available", false);
            failed.put("native_library", "qpnpu_probe_native");
            failed.put("error", exc.toString());
            failed.put("results", new JSONArray());
            failed.put("warnings", new JSONArray().put("native microbenchmarks failed; no native performance claim"));
            warnings.put("native microbenchmarks failed: " + exc);
            return failed;
        }
    }

    private JSONObject collectDeviceInfo(JSONArray warnings) throws JSONException {
        JSONObject device = new JSONObject();
        device.put("manufacturer", safe(Build.MANUFACTURER));
        device.put("model", safe(Build.MODEL));
        device.put("device", safe(Build.DEVICE));
        device.put("board", safe(Build.BOARD));
        device.put("hardware", safe(Build.HARDWARE));
        device.put("soc_manufacturer", reflectBuildString("SOC_MANUFACTURER"));
        device.put("soc_model", reflectBuildString("SOC_MODEL"));
        device.put("android_release", safe(Build.VERSION.RELEASE));
        device.put("sdk_version", Build.VERSION.SDK_INT);
        JSONArray abis = new JSONArray();
        if (Build.SUPPORTED_ABIS != null) {
            for (String abi : Build.SUPPORTED_ABIS) {
                abis.put(abi);
            }
        }
        device.put("supported_abis", abis);
        return device;
    }

    private JSONObject collectCpuInfo(JSONArray warnings) throws JSONException {
        JSONObject cpu = new JSONObject();
        cpu.put("available_processors", Runtime.getRuntime().availableProcessors());
        String cpuInfo = readTextFileBestEffort("/proc/cpuinfo", 24000);
        cpu.put("proc_cpuinfo_readable", !cpuInfo.isEmpty());
        if (cpuInfo.isEmpty()) {
            warnings.put("could not read /proc/cpuinfo");
        } else {
            cpu.put("proc_cpuinfo_excerpt", cpuInfo);
            cpu.put("string_hints", findHints(cpuInfo, new String[]{
                    "Qualcomm", "Snapdragon", "Kryo", "ARM", "AArch64", "Hardware"
            }));
        }

        JSONObject props = new JSONObject();
        String[] keys = new String[]{
                "ro.product.manufacturer",
                "ro.product.model",
                "ro.product.device",
                "ro.board.platform",
                "ro.hardware",
                "ro.soc.manufacturer",
                "ro.soc.model",
                "ro.build.version.release",
                "ro.build.version.sdk",
                "ro.opengles.version",
                "ro.hardware.egl"
        };
        for (String key : keys) {
            String value = runShellBestEffort("getprop " + key, 2000).trim();
            if (!value.isEmpty()) {
                props.put(key, value);
            }
        }
        cpu.put("selected_getprop", props);
        if (props.length() == 0) {
            warnings.put("selected getprop values were not accessible");
        }
        return cpu;
    }

    private JSONObject collectMemInfo(JSONArray warnings) throws JSONException {
        JSONObject memory = new JSONObject();
        Runtime runtime = Runtime.getRuntime();
        memory.put("runtime_max_memory_bytes", runtime.maxMemory());
        memory.put("runtime_total_memory_bytes", runtime.totalMemory());
        memory.put("runtime_free_memory_bytes", runtime.freeMemory());
        String memInfo = readTextFileBestEffort("/proc/meminfo", 12000);
        memory.put("proc_meminfo_readable", !memInfo.isEmpty());
        if (memInfo.isEmpty()) {
            warnings.put("could not read /proc/meminfo");
        } else {
            memory.put("proc_meminfo_excerpt", memInfo);
        }
        return memory;
    }

    private JSONObject collectGpuHints(JSONArray warnings) throws JSONException {
        JSONObject gpu = collectLibraryHints(new String[]{
                "vulkan", "libvulkan", "gles", "egl", "opencl", "adreno", "kgsl"
        }, new String[]{
                "libvulkan.so", "libOpenCL.so", "libOpenCL_adreno.so",
                "libGLESv2_adreno.so", "libEGL_adreno.so", "libGLESv3.so"
        }, warnings);
        boolean vulkanDetected = containsHint(gpu.optJSONArray("library_hints"), "vulkan")
                || containsHint(gpu.optJSONArray("shell_hints"), "vulkan")
                || containsHint(gpu.optJSONArray("direct_library_hints"), "vulkan");
        gpu.put("vulkan_libraries_detected", vulkanDetected);
        gpu.put("status", statusFromHints(gpu));
        gpu.put("availability_claim", "none");
        return gpu;
    }

    private JSONObject collectNpuHints(JSONArray warnings) throws JSONException {
        JSONObject npu = collectLibraryHints(new String[]{
                "libqnnhtp.so",
                "libqnnsystem.so",
                "libqnncpu.so",
                "libqnngpu.so",
                "libqnndsp.so",
                "qnn",
                "cdsp",
                "dsp",
                "hexagon",
                "htp",
                "nnapi",
                "neuralnetworks",
                "libneuralnetworks"
        }, new String[]{
                "libQnnHtp.so", "libQnnSystem.so", "libQnnCpu.so", "libQnnGpu.so",
                "libQnnDsp.so", "libSnpeHtpV81Stub.so", "libcdsprpc.so",
                "libadsprpc.so", "libneuralnetworks.so"
        }, warnings);
        boolean qnnDetected = containsHint(npu.optJSONArray("library_hints"), "qnn")
                || containsHint(npu.optJSONArray("shell_hints"), "qnn")
                || containsHint(npu.optJSONArray("direct_library_hints"), "qnn");
        boolean nnapiDetected = containsHint(npu.optJSONArray("library_hints"), "neuralnetworks")
                || containsHint(npu.optJSONArray("shell_hints"), "neuralnetworks")
                || containsHint(npu.optJSONArray("library_hints"), "nnapi")
                || containsHint(npu.optJSONArray("shell_hints"), "nnapi")
                || containsHint(npu.optJSONArray("direct_library_hints"), "neuralnetworks")
                || containsHint(npu.optJSONArray("direct_library_hints"), "nnapi");
        npu.put("qnn_libraries_detected", qnnDetected);
        npu.put("nnapi_string_hints_detected", nnapiDetected);
        npu.put("status", statusFromHints(npu));
        npu.put("availability_claim", "none; string hints are not proof of NPU availability");
        return npu;
    }

    private JSONObject collectThermalHints(JSONArray warnings) throws JSONException {
        JSONObject thermal = new JSONObject();
        JSONArray zones = new JSONArray();
        File thermalDir = new File("/sys/class/thermal");
        String[] names = thermalDir.list();
        if (names == null) {
            thermal.put("status", "unknown");
            warnings.put("/sys/class/thermal was not readable");
            thermal.put("zones", zones);
            return thermal;
        }
        Arrays.sort(names);
        int limit = Math.min(names.length, 64);
        for (int i = 0; i < limit; i++) {
            File zone = new File(thermalDir, names[i]);
            if (!zone.isDirectory()) {
                continue;
            }
            JSONObject entry = new JSONObject();
            entry.put("name", names[i]);
            String type = readTextFileBestEffort(new File(zone, "type").getAbsolutePath(), 200).trim();
            String temp = readTextFileBestEffort(new File(zone, "temp").getAbsolutePath(), 200).trim();
            if (!type.isEmpty()) {
                entry.put("type", type);
            }
            if (!temp.isEmpty()) {
                entry.put("temp_raw", temp);
            }
            zones.put(entry);
        }
        thermal.put("status", zones.length() > 0 ? "hints_detected" : "not_detected");
        thermal.put("zones", zones);
        return thermal;
    }

    private JSONObject collectLibraryHints(String[] needles, String[] directLibraryNames, JSONArray warnings) throws JSONException {
        JSONObject result = new JSONObject();
        JSONArray dirs = new JSONArray();
        JSONArray libraryHints = new JSONArray();
        boolean anyReadable = false;
        String[] paths = new String[]{
                "/vendor/lib64",
                "/vendor/lib",
                "/system/lib64",
                "/system/lib",
                "/system_ext/lib64",
                "/system_ext/lib",
                "/odm/lib64",
                "/odm/lib",
                "/product/lib64",
                "/product/lib"
        };
        for (String path : paths) {
            JSONArray names = listDirBestEffort(path, 600);
            JSONObject dir = new JSONObject();
            dir.put("path", path);
            dir.put("entry_count", names.length());
            dir.put("readable", names.length() > 0);
            dirs.put(dir);
            if (names.length() > 0) {
                anyReadable = true;
            }
            for (int i = 0; i < names.length(); i++) {
                String name = names.optString(i, "");
                if (containsAny(name, needles)) {
                    libraryHints.put(path + "/" + name);
                }
            }
        }

        String shellListing = runShellBestEffort(
                "ls /vendor/lib64 /vendor/lib /system/lib64 /system/lib /system_ext/lib64 /odm/lib64 2>/dev/null",
                30000);
        JSONArray shellHints = findHints(shellListing, needles);
        JSONArray directHints = directLibraryHints(paths, directLibraryNames);

        result.put("searched_library_dirs", dirs);
        result.put("library_hints", libraryHints);
        result.put("direct_library_hints", directHints);
        result.put("shell_hints", shellHints);
        result.put("library_dirs_readable", anyReadable);
        if (!anyReadable) {
            warnings.put("Android library directories were not readable from the app sandbox");
        }
        return result;
    }

    private JSONObject buildCapabilitySummary(JSONObject root) throws JSONException {
        JSONObject device = root.optJSONObject("device");
        JSONObject cpu = root.optJSONObject("cpu");
        JSONObject gpu = root.optJSONObject("gpu");
        JSONObject npu = root.optJSONObject("npu");
        JSONObject thermal = root.optJSONObject("thermal");

        JSONObject summary = new JSONObject();
        if (device != null) {
            summary.put("device_model", device.optString("model", ""));
            summary.put("soc_model", device.optString("soc_model", ""));
            summary.put("android_release", device.optString("android_release", ""));
        }
        if (cpu != null) {
            summary.put("available_processors", cpu.optInt("available_processors", -1));
        }
        if (gpu != null) {
            summary.put("gpu_status", gpu.optString("status", "unknown"));
            summary.put("vulkan_libraries_detected", gpu.optBoolean("vulkan_libraries_detected", false));
            summary.put("gpu_hint_count",
                    lengthOf(gpu.optJSONArray("library_hints"))
                            + lengthOf(gpu.optJSONArray("direct_library_hints"))
                            + lengthOf(gpu.optJSONArray("shell_hints")));
        }
        if (npu != null) {
            summary.put("npu_status", npu.optString("status", "unknown"));
            summary.put("qnn_libraries_detected", npu.optBoolean("qnn_libraries_detected", false));
            summary.put("nnapi_string_hints_detected", npu.optBoolean("nnapi_string_hints_detected", false));
            summary.put("npu_hint_count",
                    lengthOf(npu.optJSONArray("library_hints"))
                            + lengthOf(npu.optJSONArray("direct_library_hints"))
                            + lengthOf(npu.optJSONArray("shell_hints")));
        }
        if (thermal != null) {
            summary.put("thermal_status", thermal.optString("status", "unknown"));
            summary.put("thermal_zone_count", lengthOf(thermal.optJSONArray("zones")));
        }
        JSONObject microbenchmarks = root.optJSONObject("microbenchmarks");
        if (microbenchmarks != null) {
            summary.put("native_microbenchmarks_available", microbenchmarks.optBoolean("available", false));
            summary.put("native_microbenchmarks_passed", microbenchmarks.optBoolean("all_correctness_passed", false));
            summary.put("native_microbenchmark_count", lengthOf(microbenchmarks.optJSONArray("results")));
        }
        summary.put("availability_claim", "none; this is probe evidence only, not accelerator execution");
        return summary;
    }

    private JSONArray directLibraryHints(String[] paths, String[] libraryNames) {
        JSONArray hints = new JSONArray();
        for (String path : paths) {
            for (String libraryName : libraryNames) {
                File candidate = new File(path, libraryName);
                if (candidate.exists() && candidate.isFile()) {
                    hints.put(candidate.getAbsolutePath());
                }
            }
        }
        return hints;
    }

    private String readTextFileBestEffort(String path, int maxChars) {
        if (maxChars <= 0) {
            return "";
        }
        File file = new File(path);
        if (!file.exists() || !file.isFile()) {
            return "";
        }
        try (FileInputStream input = new FileInputStream(file)) {
            return readStream(input, maxChars);
        } catch (IOException exc) {
            return "";
        }
    }

    private JSONArray listDirBestEffort(String path, int maxEntries) {
        JSONArray array = new JSONArray();
        if (maxEntries <= 0) {
            return array;
        }
        File dir = new File(path);
        String[] names = dir.list();
        if (names == null) {
            return array;
        }
        Arrays.sort(names);
        int limit = Math.min(names.length, maxEntries);
        for (int i = 0; i < limit; i++) {
            array.put(names[i]);
        }
        return array;
    }

    private String runShellBestEffort(String command, int maxChars) {
        Process process = null;
        try {
            process = Runtime.getRuntime().exec(new String[]{"sh", "-c", command});
            boolean done = process.waitFor(2, TimeUnit.SECONDS);
            if (!done) {
                process.destroy();
                return "";
            }
            String stdout = readStream(process.getInputStream(), maxChars);
            String stderr = readStream(process.getErrorStream(), Math.min(1000, maxChars));
            if (!stderr.trim().isEmpty()) {
                return stdout + "\n[stderr]\n" + stderr;
            }
            return stdout;
        } catch (Exception exc) {
            return "";
        } finally {
            if (process != null) {
                process.destroy();
            }
        }
    }

    private String saveAndFinalizeJson(JSONObject probe) throws JSONException {
        JSONArray warnings = probe.optJSONArray("warnings");
        if (warnings == null) {
            warnings = new JSONArray();
            probe.put("warnings", warnings);
        }

        File dir = getExternalFilesDir(null);
        if (dir == null) {
            warnings.put("getExternalFilesDir(null) returned null; probe_result.json was not saved");
            return probe.toString(2);
        }

        File out = new File(dir, "probe_result.json");
        probe.put("output_file", out.getAbsolutePath());
        String json = probe.toString(2);
        try {
            writeText(out, json);
        } catch (IOException exc) {
            warnings.put("failed to save probe_result.json: " + exc.getMessage());
            json = probe.toString(2);
        }
        return json;
    }

    private void logProbeJson(String json) {
        logJsonWithMarkers(JSON_BEGIN, JSON_END, json);
    }

    private void logNativeBenchmarkJson(String json) {
        logJsonWithMarkers(NATIVE_JSON_BEGIN, NATIVE_JSON_END, json);
    }

    private void logPhase6Json(String json) {
        logJsonWithMarkers(PHASE6_JSON_BEGIN, PHASE6_JSON_END, json);
    }


    private void logPhase7AJson(String json) {
        logJsonWithMarkers(PHASE7A_JSON_BEGIN, PHASE7A_JSON_END, json);
    }
    private void logJsonWithMarkers(String begin, String endMarker, String json) {
        Log.i(TAG, begin);
        for (int start = 0; start < json.length(); start += LOG_CHUNK_SIZE) {
            int end = Math.min(json.length(), start + LOG_CHUNK_SIZE);
            Log.i(TAG, json.substring(start, end));
        }
        Log.i(TAG, endMarker);
    }

    private void saveJsonToExternalFile(JSONObject payload, String fileName, JSONArray warnings) throws JSONException {
        File dir = getExternalFilesDir(null);
        if (dir == null) {
            warnings.put("getExternalFilesDir(null) returned null; " + fileName + " was not saved");
            return;
        }
        File out = new File(dir, fileName);
        payload.put("output_file", out.getAbsolutePath());
        try {
            writeText(out, payload.toString(2));
        } catch (IOException exc) {
            warnings.put("failed to save " + fileName + ": " + exc.getMessage());
        }
    }

    private void writeText(File file, String text) throws IOException {
        File parent = file.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IOException("could not create directory: " + parent);
        }
        try (FileOutputStream output = new FileOutputStream(file)) {
            output.write(text.getBytes(StandardCharsets.UTF_8));
        }
    }

    private String readStream(InputStream input, int maxChars) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[4096];
        int total = 0;
        while (total < maxChars) {
            int allowed = Math.min(buffer.length, maxChars - total);
            int read = input.read(buffer, 0, allowed);
            if (read < 0) {
                break;
            }
            output.write(buffer, 0, read);
            total += read;
        }
        return new String(output.toByteArray(), StandardCharsets.UTF_8);
    }

    private JSONArray findHints(String text, String[] needles) {
        JSONArray matches = new JSONArray();
        if (text == null || text.isEmpty()) {
            return matches;
        }
        String[] lines = text.split("\\r?\\n");
        for (String line : lines) {
            if (containsAny(line, needles)) {
                matches.put(line.trim());
                if (matches.length() >= 120) {
                    break;
                }
            }
        }
        return matches;
    }

    private boolean containsHint(JSONArray array, String needle) {
        if (array == null) {
            return false;
        }
        String lowerNeedle = needle.toLowerCase(Locale.US);
        for (int i = 0; i < array.length(); i++) {
            if (array.optString(i, "").toLowerCase(Locale.US).contains(lowerNeedle)) {
                return true;
            }
        }
        return false;
    }

    private boolean containsAny(String value, String[] needles) {
        String lower = value.toLowerCase(Locale.US);
        for (String needle : needles) {
            if (lower.contains(needle.toLowerCase(Locale.US))) {
                return true;
            }
        }
        return false;
    }

    private String statusFromHints(JSONObject object) {
        JSONArray libraries = object.optJSONArray("library_hints");
        JSONArray direct = object.optJSONArray("direct_library_hints");
        JSONArray shell = object.optJSONArray("shell_hints");
        if ((libraries != null && libraries.length() > 0)
                || (direct != null && direct.length() > 0)
                || (shell != null && shell.length() > 0)) {
            return "hints_detected";
        }
        if (object.optBoolean("library_dirs_readable", false)) {
            return "not_detected";
        }
        return "unknown";
    }

    private String reflectBuildString(String fieldName) {
        try {
            Field field = Build.class.getField(fieldName);
            Object value = field.get(null);
            return value == null ? "" : String.valueOf(value);
        } catch (Exception exc) {
            return "";
        }
    }

    private int lengthOf(JSONArray array) {
        return array == null ? 0 : array.length();
    }

    private String utcNow() {
        SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US);
        format.setTimeZone(TimeZone.getTimeZone("UTC"));
        return format.format(new Date());
    }

    private String safe(String value) {
        return value == null ? "" : value;
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }
}

