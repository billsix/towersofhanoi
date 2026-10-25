#!/usr/bin/env bash
#
# 02-install-emsdk.sh -- install the Emscripten SDK (for `make webassembly`) at a PINNED
# version into /opt/emsdk. There is no official Fedora emscripten package; the canonical,
# reproducible path is the emsdk cloned + a pinned version installed (NOT `latest`, which
# drifts). emsdk ships its own prebuilt clang/node/binaryen (~1-1.5 GB) and installs
# nothing system-wide. Prereqs (git, python3) come from 01-install-cpp-base.sh.
#
# This is the one-cohesive-build exception to "scripts take no flags": it reads the pin
# from the EMSDK_VERSION env the Dockerfile passes. Run 01-install-cpp-base.sh first.
# Reference: tasks/reference/imgui-cpp-native-and-wasm.md.
set -euo pipefail

: "${EMSDK_VERSION:?02-install-emsdk.sh: set EMSDK_VERSION (the pinned emsdk release, e.g. 3.1.74)}"

if ! command -v git >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
    echo "02-install-emsdk.sh: needs git + python3 (run 01-install-cpp-base.sh first)." >&2
    exit 1
fi

git clone https://github.com/emscripten-core/emsdk.git /opt/emsdk
cd /opt/emsdk
./emsdk install "$EMSDK_VERSION"
./emsdk activate "$EMSDK_VERSION"
# Shrink the layer: the download cache is not needed after activation.
rm -rf /opt/emsdk/downloads
