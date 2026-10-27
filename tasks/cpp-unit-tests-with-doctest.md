# C++ unit tests for the `cpp/` engine (doctest framework) + a `make test` gate

**Status:** proposed — needs go-ahead.
**Priority:** 4
**Difficulty:** 4
**Created:** 2026-10-27 (William Emerison Six <billsix@gmail.com>)
**Updated:** 2026-10-27 (William Emerison Six <billsix@gmail.com>)

## BLUF

The C++ subproject (`cpp/`) has **no unit tests and no `make test` target** — the engine
(`cpp/src/{model,presenter,recipe}.hpp`, header-only) is exercised only by playing the GUIs. This
task adds a C++ unit-test suite using the **`doctest`** framework (github.com/doctest/doctest) and a
`make test` gate (`test: image`, runs `ctest` in-container). Done: the engine has tests at parity
with the Python oracle's engine tests, `make test` builds and runs them green in the container, and
`cpp/CLAUDE.md` + the root `CLAUDE.md` document the target.

**This is a prerequisite for [[github-actions-format-test-typecheck-ci]]** — that task's C++ CI job
runs this `make test`.

## Context (cold start)

- Repo: github.com/billsix/towersofhanoi (mounted as `hanoi`), on branch `cicd`. C++ subproject
  under `cpp/`: a header-only engine in `cpp/src/` + two GUIs (`main.cpp` Dear ImGui native/wasm,
  `hanoiwx.cpp` wxWidgets) built from one `CMakeLists.txt` (`project(hanoi_cpp CXX)`,
  `add_executable(hanoi-cpp …)`, `add_executable(hanoi-wx …)`). No `enable_testing()`/`add_test()`
  today, and `cpp/Makefile` has `format`/`gui`/`wx`/`webassembly`/`serve` but **no `test`**.
- The **Python package is the behaviour oracle** (`python/src/hanoigame/`); its `tests/` and the new
  doctests define what the engine must do. The C++ engine mirrors it, so the C++ tests mirror the
  Python engine tests (model moves/win-condition, presenter layout/labelling/render, recipe
  rebinding/replay).
- Convention for vendored source deps: hanoi already vendors Dear ImGui under `cpp/imgui/` with a
  `make update-imgui` target. A single-header test framework follows the same "vendor by source"
  pattern (see `~/.claude/reference/vendoring-third-party-source-deps.md`).

## Why doctest (the framework investigation)

Investigated 2026-10-27 (the maintainer asked for a doctest-like C++ framework specifically):

- **`doctest`** (github.com/doctest/doctest) — single-header, **modeled on Catch2** but the
  fastest-compiling option, and uniquely designed so **tests can live right next to the production
  code** and be compiled out of release binaries (`DOCTEST_CONFIG_DISABLE`). That "tests beside the
  code" property is the C++ analogue of the Python/Rust **doctests-by-default** direction already
  adopted repo-wide, and the name is literally "doctest" — **the recommended choice.**
- **Catch2** (github.com/catchorg/Catch2) — also header-only, more feature-rich (matchers, data
  generators, microbenchmarks), heavier compile. doctest's syntax is a near-subset, so a later move
  to Catch2 is cheap. The extra features aren't needed for a small deterministic engine.
- GoogleTest / Boost.Test — heavier, need linking/build integration; not single-header; rejected for
  a small header-only engine.

Sources: [hackingcpp testing frameworks](https://hackingcpp.com/cpp/tools/testing_frameworks.html),
[doctest FAQ](https://k1.spdns.de/Develop/Projects/pico/kilipili/extern/doctest/doc/markdown/faq.md),
[Catch2 vs doctest comparison](https://kindatechnical.com/c-plus-plus/catch2-doctest-header-only-testing.html).

## Plan

1. **Vendor the single header** `doctest.h` under `cpp/` (e.g. `cpp/doctest/doctest.h`, mirroring the
   `cpp/imgui/` layout) and add a `make update-doctest DOCTEST_REF=<tag>` target + `tools/` script,
   per the source-dep vendoring convention (print the vendored `DOCTEST_VERSION`).
2. **Write the tests inline in the engine headers** (decision below), mirroring the Python engine
   suite — model (legal/illegal moves, win condition), presenter (layout maths, the six labellings,
   `render` board strings including the 0-disc empty case), recipe (rebinding, rebound moves, replay
   under relabelling). Each `TEST_CASE` sits beside the code it tests, wrapped in
   `#ifndef DOCTEST_CONFIG_DISABLE` so the GUI binaries (`hanoi-cpp`, `hanoi-wx`) compile the tests
   out: build those targets with `-DDOCTEST_CONFIG_DISABLE`, and the test executable without it.
3. **Wire into CMake + ctest:** a test executable (`add_executable(hanoi-tests …)` whose one `.cpp`
   defines `DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN` and includes the engine headers *without*
   `DOCTEST_CONFIG_DISABLE`, so the inline `TEST_CASE`s are collected), `enable_testing()` +
   `add_test(NAME … )`, so `ctest` runs it. The GUI targets add `DOCTEST_CONFIG_DISABLE` to their
   compile definitions.
4. **Add `make test`** to `cpp/Makefile` (`test: image`, `$(CONTAINER_CMD) run … ctest --output-on-failure`
   in the build dir), mirroring `shell`'s env / `PODMAN_RUN_FLAGS`, standalone like `format` (nothing
   interactive depends on it).
5. **Verify green nested**, update `cpp/CLAUDE.md` + root `CLAUDE.md` (target lists + the
   doctest-by-default convention already noted there), and consider feeding the C++ angle back to
   `~/.claude/reference/doctests-by-default.md` (a new `## C++` section — the doctest framework makes
   "tests beside the code" literally true in C++ too).

## Decisions (resolved with the maintainer, 2026-10-27)

1. **Framework = `doctest`** (github.com/doctest/doctest) — the doctest-like, fastest-compiling,
   tests-beside-code option. Not Catch2.
2. **Placement = inline in the engine headers** (doctest's beside-the-code mode), gated out of the
   GUI binaries with `DOCTEST_CONFIG_DISABLE` — matching the Python/Rust doctest-by-default direction
   the repo just adopted. Not a separate `cpp/tests/` TU.
