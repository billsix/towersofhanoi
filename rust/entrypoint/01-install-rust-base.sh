#!/usr/bin/env bash
#
# 01-install-rust-base.sh -- the Rust toolchain plus the full native build stack
# wxDragon needs, so the Rust ports (the workspace: hanoi, hanoi-cli, hanoi-gui) and the
# Tauri front-end build and run in the container. This is the BASE for the hanoi Rust
# subproject (there is no Python base here -- the folder is self-contained).
#
# wxDragon's GUI build needs a complete native toolchain because `wxdragon-sys`:
#   1. runs bindgen over its C++ header -> needs libclang (clang-devel).
#   2. downloads wxWidgets 3.3.4 over HTTPS and builds it statically -> needs a C/C++
#      compiler (gcc/gcc-c++), make + cmake + ninja-build, the GTK/X11 dev headers
#      (gtk3-devel, pulled by wxGTK-devel), and openssl-devel for the download crate.
#   3. links the SYSTEM image libraries: png + zlib via gtk3-devel, but jpeg/tiff/expat
#      need their own -devel (libjpeg-turbo-devel / libtiff-devel / expat-devel).
#   4. links the X11 session libs -> libSM-devel / libICE-devel.
#
# The Tauri front-end renders in the OS webview (WebKitGTK on Linux), so it needs
# webkit2gtk4.1-devel + libsoup3-devel.
#
# rust-analyzer is installed for the emacs LSP set (entrypoint/dotfiles/.emacs.d).
#
# CAVEAT (self-contained-image rule): wxDragon fetches wxWidgets at cargo-build time, so
# a Rust-GUI build needs network and is NOT offline-reproducible as-is (point
# WXDRAGON_SYS_BUILD_DIR at a pre-vendored wx source to fix that). The Makefile caches
# the build in .container-target so the minutes-long first build is not repeated.
#
# One package group per script, no options (see the project template). Single dnf call,
# so its own exit status is the gate.
set -uo pipefail

if ! command -v dnf >/dev/null 2>&1; then
    echo "01-install-rust-base.sh: needs 'dnf' (this installs Fedora packages), not found." >&2
    echo "Run on a Fedora host/guest, or inside the project's Fedora-based image." >&2
    exit 1
fi

dnf install -y cargo \
               clang-devel \
               cmake \
               expat-devel \
               gcc \
               gcc-c++ \
               git \
               libICE-devel \
               libjpeg-turbo-devel \
               libSM-devel \
               libsoup3-devel \
               libtiff-devel \
               make \
               nano \
               ninja-build \
               openssl-devel \
               rust \
               rust-analyzer \
               rustfmt \
               tmux \
               webkit2gtk4.1-devel \
               wxGTK-devel
