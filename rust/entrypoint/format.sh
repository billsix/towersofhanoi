#!/bin/env bash
# Format the Rust workspace with rustfmt (cargo fmt). Portable: the cd no-ops on a host
# caller already in rust/.
[ -d /hanoi-rust ] && cd /hanoi-rust
export CARGO_TARGET_DIR=${CARGO_TARGET_DIR:-/hanoi-rust/.container-target}
export CARGO_HOME=${CARGO_HOME:-/hanoi-rust/.container-cargo}

status=0
cargo fmt --all || status=1
# The Tauri crate is not a workspace member, so format it separately.
( cd tauri/src-tauri && cargo fmt ) || status=1
exit $status
