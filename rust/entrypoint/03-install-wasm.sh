#!/usr/bin/env bash
#
# 03-install-wasm.sh -- the WebAssembly toolchain for the egui web build
# (`make egui-web` / `make egui-serve`): the wasm32-unknown-unknown Rust std library
# and `trunk` (the Rust/WASM web bundler). Both are Fedora packages, so this bakes them
# into the image like any other rpm -- no `cargo install`, no network at build beyond dnf,
# and the web build runs offline against the baked toolchain afterwards.
#
# Gated by the Dockerfile's USE_WASM ARG (Makefile default 1; a lean MINIMAL_IMAGE build
# drops it). Host-runnable with no container runtime. One package group, single dnf call,
# so its own exit status is the gate (the project template).
set -uo pipefail

if ! command -v dnf >/dev/null 2>&1; then
    echo "03-install-wasm.sh: needs 'dnf' (this installs Fedora packages), not found." >&2
    echo "Run on a Fedora host/guest, or inside the project's Fedora-based image." >&2
    exit 1
fi

dnf install -y rust-std-static-wasm32-unknown-unknown \
               trunk
