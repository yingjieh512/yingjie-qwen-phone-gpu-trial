cmake_minimum_required(VERSION 3.20)
project(qpnpu_native LANGUAGES CXX)

add_library(qpnpu_native INTERFACE)
target_compile_features(qpnpu_native INTERFACE cxx_std_17)
target_include_directories(qpnpu_native INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/include)

