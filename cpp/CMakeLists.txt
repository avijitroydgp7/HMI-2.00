cmake_minimum_required(VERSION 3.14)
project(scene_utils)

find_package(pybind11 REQUIRED)

pybind11_add_module(scene_utils MODULE scene_utils.cpp)

set_target_properties(scene_utils PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/..
)