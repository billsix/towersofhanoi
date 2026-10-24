#!/bin/env bash
# Default entrypoint for the Rust subproject: run the library/logic test gate. This
# builds the shared `hanoigame` crate and its tests only -- NOT the wxDragon GUI (whose
# from-source wxWidgets build is slow and network-dependent); run that via `make wx`.
set -e
cd /hanoi-rust
export CARGO_TARGET_DIR=/hanoi-rust/.container-target
export CARGO_HOME=/hanoi-rust/.container-cargo
cargo test -p hanoigame -p hanoi-cli -p hanoi
