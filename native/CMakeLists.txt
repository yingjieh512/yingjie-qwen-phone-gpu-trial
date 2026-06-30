cmake_minimum_required(VERSION 3.20)
project(qpnpu_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(qpnpu_native STATIC
  src/tensor.cpp
  src/runtime.cpp
  src/model.cpp
  src/probe.cpp
  backends/cpu/cpu_backend.cpp
  backends/cpu/int4_matvec.cpp
  backends/cpu/rmsnorm.cpp
  backends/cpu/rope.cpp
  backends/cpu/softmax.cpp
  backends/vulkan/vulkan_backend.cpp
  backends/nnapi/nnapi_backend.cpp
  backends/qnn_stub/qnn_backend.cpp
)

target_include_directories(qpnpu_native
  PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_compile_features(qpnpu_native PUBLIC cxx_std_17)

add_executable(qpnpu_microbench tools/qpnpu_microbench.cpp)
target_link_libraries(qpnpu_microbench PRIVATE qpnpu_native)

include(CTest)
if(BUILD_TESTING)
  function(add_qpnpu_test name source)
    add_executable(${name} ${source})
    target_link_libraries(${name} PRIVATE qpnpu_native)
    add_test(NAME ${name} COMMAND ${name})
  endfunction()

  add_qpnpu_test(test_int4_matvec tests/test_int4_matvec.cpp)
  add_qpnpu_test(test_rmsnorm tests/test_rmsnorm.cpp)
  add_qpnpu_test(test_rope tests/test_rope.cpp)
  add_qpnpu_test(test_softmax tests/test_softmax.cpp)
  add_qpnpu_test(test_backend_availability tests/test_backend_availability.cpp)
endif()