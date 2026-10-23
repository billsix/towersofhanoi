#!/usr/bin/env bash
#
# 04-install-rust.sh -- the Rust toolchain plus the full native build stack
# wxDragon needs, so the Rust ports (the rust/ workspace: hanoi, hanoi-cli,
# hanoi-gui) build and run in the container alongside the Python ones.
#
# This image's base (01-install-base.sh) is deliberately Python-only -- it has
# NO C/C++ compiler. wxDragon's GUI build needs a complete native toolchain
# because `wxdragon-sys`:
#   1. runs **bindgen** over its C++ header -> needs **libclang** (clang-devel,
#      which pulls clang-libs/libclang.so); without it: "Unable to find libclang".
#   2. **downloads the wxWidgets 3.3.4 source over HTTPS and builds it statically**
#      (it does NOT use the system wxGTK) -> needs a C/C++ compiler (gcc/gcc-c++),
#      make + cmake + ninja-build for the wxWidgets cmake build, the GTK/X11 dev
#      headers (gtk3-devel, pulled by wxGTK-devel), and openssl-devel so the
#      reqwest/openssl-sys download crate compiles ("Package 'openssl' not found").
#   3. links the SYSTEM image libraries (it does NOT vendor its own): png + zlib
#      arrive via gtk3-devel, but **jpeg, tiff and expat need their own -devel**
#      (libjpeg-turbo-devel / libtiff-devel / expat-devel) or the final link of a
#      binary fails "cannot find -ljpeg / -lexpat / -ltiff".
#   4. links the X11 session libs -> libSM-devel / libICE-devel (their -devel
#      `.so` symlinks; else "cannot find -lSM / -lICE").
#
# The Tauri port (tauri/) is a fifth front-end over the same hanoigame crate; it
# renders in the OS webview. On Linux that is WebKitGTK, so its backend needs
# **webkit2gtk4.1-devel** (the Tauri v2 webview dep) and **libsoup3-devel** (the
# HTTP/session library WebKitGTK 4.1 links) -- without them `cargo run` in
# tauri/src-tauri fails "Package 'webkit2gtk-4.1' / 'libsoup-3.0' not found".
#
# CAVEAT (self-contained-image rule): wxDragon fetches wxWidgets at cargo-build
# time, so a Rust-GUI build needs network and is NOT offline-reproducible as-is
# (point WXDRAGON_SYS_BUILD_DIR at a pre-vendored wx source to fix that). The
# Makefile caches the build in rust/.container-target so the ~minutes-long first
# build is not repeated every run.
#
# One package group per script, no options (see 01-install-base.sh). Run
# 01-install-base.sh first. Single dnf call, so its own exit status is the gate.
set -uo pipefail

if ! command -v dnf >/dev/null 2>&1; then
    echo "04-install-rust.sh: needs 'dnf' (this installs Fedora packages), not found." >&2
    echo "Run on a Fedora host/guest, or inside the project's Fedora-based image." >&2
    exit 1
fi

dnf install -y cargo \
               clang-devel \
               cmake \
               expat-devel \
               gcc \
               gcc-c++ \
               libICE-devel \
               libjpeg-turbo-devel \
               libSM-devel \
               libsoup3-devel \
               libtiff-devel \
               make \
               ninja-build \
               openssl-devel \
               rust \
               rustfmt \
               webkit2gtk4.1-devel \
               wxGTK-devel
