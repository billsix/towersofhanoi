#!/bin/env bash
# Format the Rust workspace with rustfmt (cargo fmt) and the Tauri frontend's static web
# files with `deno fmt`. Portable: the cd no-ops on a host caller already in rust/.
[ -d /hanoi-rust ] && cd /hanoi-rust
export CARGO_TARGET_DIR=${CARGO_TARGET_DIR:-/hanoi-rust/.container-target}
export CARGO_HOME=${CARGO_HOME:-/hanoi-rust/.container-cargo}

status=0
cargo fmt --all || status=1
# The Tauri crate is not a workspace member, so format it separately.
( cd tauri/src-tauri && cargo fmt ) || status=1
# The Tauri frontend's vanilla web files (index.html/main.js/style.css) -- deno fmt, one
# binary, no Node (scope from tauri/frontend/deno.json's fmt.include). deno absent on a
# bare host, so guard it; the container's type-check gate runs `deno fmt --check`.
if command -v deno >/dev/null 2>&1; then
  ( cd tauri/frontend && deno fmt ) || status=1
fi
exit $status
