cmake_minimum_required(VERSION 3.22.1)

project(qpnpu_probe_native LANGUAGES CXX)

add_library(qpnpu_probe_native SHARED
    qpnpu_probe_native.cpp
    qpnpu_phase6_native.cpp
)

target_compile_features(qpnpu_probe_native PRIVATE cxx_std_17)
target_compile_options(qpnpu_probe_native PRIVATE -Wall -Wextra -Werror)
target_link_options(qpnpu_probe_native PRIVATE
    "-Wl,-z,max-page-size=16384"
    "-Wl,-z,common-page-size=16384"
)

find_library(log-lib log)
find_library(dl-lib dl)
target_link_libraries(qpnpu_probe_native PRIVATE ${log-lib} ${dl-lib})
