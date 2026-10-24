#!/usr/bin/env bash
#
# 01-install-cpp-base.sh -- the C++ toolchain + the SDL2/OpenGL stack the Dear ImGui GUI
# needs, for the hanoi C++ subproject. This is the BASE (the folder is self-contained).
#
# Native ImGui app build: a C++ compiler + SDL2 + OpenGL. On Fedora 42+ `SDL2-devel` is a
# virtual provide satisfied by `sdl2-compat-devel` (the SDL2 API/ABI shim over SDL3);
# `sdl2-config`/`sdl2.pc` still work. `mesa-libGL-devel` provides libGL/GL/gl.h for -lGL;
# `mesa-dri-drivers` gives software rendering so the GUI can run headless/CI
# (LIBGL_ALWAYS_SOFTWARE=1). clang + clang-tools-extra provide clangd for the emacs LSP.
# git + python3 are the emsdk prerequisites (see 02-install-emsdk.sh); see the reference
# doc tasks/reference/imgui-cpp-native-and-wasm.md.
#
# One package group per script, no options. Single dnf call, so its own exit status is the gate.
set -uo pipefail

if ! command -v dnf >/dev/null 2>&1; then
    echo "01-install-cpp-base.sh: needs 'dnf' (this installs Fedora packages), not found." >&2
    echo "Run on a Fedora host/guest, or inside the project's Fedora-based image." >&2
    exit 1
fi

dnf install -y gcc \
               gcc-c++ \
               clang \
               clang-tools-extra \
               cmake \
               ninja-build \
               make \
               git \
               python3 \
               tmux \
               nano \
               SDL2-devel \
               mesa-libGL-devel \
               mesa-dri-drivers
