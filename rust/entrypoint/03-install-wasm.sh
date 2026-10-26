#!/usr/bin/env bash
#
# 03-install-wasm.sh -- the WebAssembly toolchain for the egui web build
# (`make egui-web` / `make egui-serve`): the wasm32-unknown-unknown Rust std library,
# `trunk` (the Rust/WASM web bundler), and the `wasm-bindgen` CLI that trunk drives.
#
# The wasm32 std + trunk are Fedora packages, baked like any rpm. `wasm-bindgen` is NOT
# packaged: trunk normally downloads the matching CLI the first time it runs and caches it
# under ~/.cache/trunk -- but each `make egui-*` runs a fresh --rm container, so that cache
# starts empty and trunk re-downloads every run. We pre-place the exact version into that
# cache at image-build time (outside the /hanoi-rust bind-mount, so it survives into the
# image and every fresh container reuses it -- no runtime download). trunk reuses a
# cache-resident binary in normal mode (verified); this is the "self-contained image" rule
# applied to trunk's one tool.
#
# The version MUST match the `wasm-bindgen` crate in hanoi-egui/Cargo.lock, or trunk will
# ignore the baked copy and download the right one. The Dockerfile passes it from the
# Makefile (which reads Cargo.lock); the default here is the fallback for a host run.
#
# Gated by the Dockerfile's USE_WASM ARG (Makefile default 1; a lean MINIMAL_IMAGE build
# drops it). Host-runnable with no container runtime. Multi-step, so accumulate status
# (the multi-step-gate rule), not a bare sequence.
set -uo pipefail

WASM_BINDGEN_VERSION="${WASM_BINDGEN_VERSION:-0.2.129}"

if ! command -v dnf >/dev/null 2>&1; then
    echo "03-install-wasm.sh: needs 'dnf' (this installs Fedora packages), not found." >&2
    echo "Run on a Fedora host/guest, or inside the project's Fedora-based image." >&2
    exit 1
fi

status=0

# wasm32 std + trunk (rpms), plus curl/tar for the wasm-bindgen fetch below.
dnf install -y rust-std-static-wasm32-unknown-unknown \
               trunk \
               curl \
               tar || status=1

# Pre-place the wasm-bindgen CLI into trunk's tool cache (~/.cache/trunk) so trunk finds
# it instead of downloading at runtime. The release ships a static musl binary.
cache_dir="${HOME:-/root}/.cache/trunk/wasm-bindgen-${WASM_BINDGEN_VERSION}"
asset="wasm-bindgen-${WASM_BINDGEN_VERSION}-x86_64-unknown-linux-musl"
url="https://github.com/rustwasm/wasm-bindgen/releases/download/${WASM_BINDGEN_VERSION}/${asset}.tar.gz"
if [ -x "${cache_dir}/wasm-bindgen" ]; then
    echo "wasm-bindgen ${WASM_BINDGEN_VERSION} already cached at ${cache_dir}"
else
    workdir="$(mktemp -d)"
    if curl -fsSL "$url" -o "${workdir}/wb.tar.gz" \
        && tar -xzf "${workdir}/wb.tar.gz" -C "$workdir"; then
        mkdir -p "$cache_dir"
        install -m 0755 "${workdir}/${asset}/wasm-bindgen" "${cache_dir}/wasm-bindgen" || status=1
        echo "baked wasm-bindgen into ${cache_dir}: $("${cache_dir}/wasm-bindgen" --version 2>/dev/null)"
    else
        echo "03-install-wasm.sh: failed to fetch wasm-bindgen ${WASM_BINDGEN_VERSION} from ${url}" >&2
        status=1
    fi
    rm -rf "$workdir"
fi

exit $status
