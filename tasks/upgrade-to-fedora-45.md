# Upgrade the container base from Fedora 44 to Fedora 45

**Status:** in progress
**Priority:** 3
**Difficulty:** 6

## BLUF
Bump all four Dockerfiles (`Dockerfile`, `python/`, `cpp/`, `rust/`) to
`fedora:45` and build each sub-project nested. "Done" = each per-language image
builds on 45 (python: pytest/doctests; rust: cargo check/test; cpp: ImGui/SDL2/GL
build + ctest doctests).

## Context
Fleet-wide Fedora 44 → 45 bump (William Emerison Six <billsix@gmail.com>,
2026-11-05). Fedora 45: GCC 16.2 / clang LLVM 23, Python 3.15, Rust via rustup/
dnf. Three toolchains, three risk classes: Python 3.15 wheels (python/), new
clang/GCC C++ diagnostics (cpp/), and Rust edition/deps (rust/). Build each
sub-dir's `make image` (and `make check`/`test` where present).

## Plan
1. Bump all four FROM lines. 2. Build python/, rust/, cpp/ in turn nested.
3. Fix per-toolchain breakage minimally (discretion; log here). 4. Stage by path;
archive.

## Notes / findings
(appended as each sub-build runs)
