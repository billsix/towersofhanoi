# Upgrade the container base from Fedora 44 to Fedora 45 (done)

Done 2026-11-05 (William Emerison Six <billsix@gmail.com>). Part of a fleet-wide
Fedora 44 -> 45 bump.

## What changed

- Bumped all four Dockerfiles to `fedora:45`: `Dockerfile` (Sphinx book),
  `python/Dockerfile`, `cpp/Dockerfile`, `rust/Dockerfile`.

No source changes. All four `make image` builds green nested on the 45 base:
- **python/** (Python 3.15): pure-Python deps (pytest/pluggy/Pygments/termcolor),
  wxPython from dnf -- installed fine, no cp315 wheel issues.
- **rust/**: cargo build/check clean.
- **cpp/**: the ImGui/SDL2/GL build + ctest doctests clean under clang LLVM 23
  (no new -Werror diagnostics hit here).
- **book** (top): the Sphinx + TeX-Live docs toolchain built on 45.

Images `localhost/hanoi-*:latest`.
