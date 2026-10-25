#!/bin/env bash
# Default entrypoint for the C++ subproject: configure + build the native target (the
# gate). The wasm build is `make webassembly`; running the GUI is `make gui`.
set -e
cd /hanoi-cpp
cmake -S . -B build -G Ninja -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build
