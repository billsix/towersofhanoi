# Rust subproject dev-shell setup. Point cargo at caches on the bind-mount (both
# gitignored) so repeat builds are fast and the heavy wxDragon from-source wxWidgets
# build is done once: CARGO_TARGET_DIR holds compiled artifacts, CARGO_HOME holds the
# crate-registry download cache. Neither clashes with the host's own target/ or ~/.cargo.
set -e
cd /hanoi-rust
export CARGO_TARGET_DIR=/hanoi-rust/.container-target
export CARGO_HOME=/hanoi-rust/.container-cargo
# No args -> interactive shell. Args (a `-c '...'` payload from `make shell-exec`) ->
# run them after setup, in a fresh bash not under -e.
exec bash "$@"
