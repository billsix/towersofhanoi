#!/bin/bash
# Install a pinned Deno to /usr/local/bin, for the JavaScript type-check gate
# (`deno check` / `deno lint` / `deno fmt` over the Tauri frontend's vanilla JS).
# Deno is ONE signed binary: no node_modules, no lockfile, no transitive deps, and
# npm lifecycle scripts are off by default -- so the gate carries no npm supply-chain
# surface. See ~/.claude/reference/javascript-coding-standard.md.
#
# Host-runnable (needs curl + unzip; uses dnf for them when present). Network is used
# at image-build time only; the baked binary type-checks local files offline after.
# Pin with DENO_VERSION (the Dockerfile passes it); the default tracks a known-good tag.
set -e

DENO_VERSION="${DENO_VERSION:-v2.9.8}"
ASSET="deno-x86_64-unknown-linux-gnu.zip"
BASE="https://github.com/denoland/deno/releases/download/${DENO_VERSION}"

if command -v dnf >/dev/null 2>&1; then
  dnf install -y unzip curl
fi

workdir="$(mktemp -d)"
cd "$workdir"
curl -fsSL -o "$ASSET" "${BASE}/${ASSET}"
curl -fsSL -o "${ASSET}.sha256sum" "${BASE}/${ASSET}.sha256sum"
# The .sha256sum asset is "<hash>  <filename>"; verify before trusting the binary.
sha256sum -c "${ASSET}.sha256sum"
unzip -o "$ASSET" -d /usr/local/bin
chmod +x /usr/local/bin/deno
cd /
rm -rf "$workdir"

/usr/local/bin/deno --version
