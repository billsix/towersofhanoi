# C++ unit tests for the `cpp/` engine (doctest framework) + a `make test` gate

**Status:** done (staged; awaiting the maintainer's commit, then archive).
**Priority:** 4
**Difficulty:** 4
**Created:** 2026-10-27 (William Emerison Six <billsix@gmail.com>)
**Updated:** 2026-10-27 (William Emerison Six <billsix@gmail.com>)

## BLUF

The C++ subproject (`cpp/`) had **no unit tests and no `make test`** — the header-only engine
(`cpp/src/{model,presenter,recipe}.hpp`) was exercised only by playing the GUIs. This task added a
C++ unit-test suite with the **`doctest`** framework (github.com/doctest/doctest), the `TEST_CASE`s
**collocated inline** beside the engine code, and a `make test` gate (`ctest`). Done: `make test`
is green (16 cases / 73 assertions), the GUI binaries compile the tests out
(`-DDOCTEST_CONFIG_DISABLE`), and the docs record the convention.

**This unblocks [[github-actions-format-test-typecheck-ci]]** — that task's C++ CI job runs this
`make test`.

## Context (cold start)

- Repo: github.com/billsix/towersofhanoi (mounted as `hanoi`), branch `cicd`. C++ subproject under
  `cpp/`: a header-only engine in `cpp/src/` + two GUIs (`main.cpp` Dear ImGui native/wasm,
  `hanoiwx.cpp` wxWidgets) from one `CMakeLists.txt`. The **Python package is the behaviour oracle**;
  the C++ engine mirrors it, so the C++ tests mirror the Python engine tests. The C++ presenter does
  **not** port the ASCII-render maths (the GUI draws primitives), so there are no render tests.

## Why doctest (the framework investigation)

Investigated 2026-10-27 (the maintainer asked for a doctest-like C++ framework specifically):

- **`doctest`** (github.com/doctest/doctest) — single-header, **modeled on Catch2** but the
  fastest-compiling option, and uniquely designed so **tests live right next to the production code**
  and compile out of release binaries (`DOCTEST_CONFIG_DISABLE`). That "tests beside the code"
  property is the C++ analogue of the Python/Rust **doctests-by-default** direction, and the name is
  literally "doctest" — the chosen framework.
- **Catch2** — also header-only, more features, heavier compile; doctest's syntax is a near-subset,
  so a later switch is cheap. GoogleTest / Boost.Test — heavier, need linking; rejected for a small
  header-only engine.

Sources: [hackingcpp testing frameworks](https://hackingcpp.com/cpp/tools/testing_frameworks.html),
[doctest FAQ](https://k1.spdns.de/Develop/Projects/pico/kilipili/extern/doctest/doc/markdown/faq.md).

## Decisions (resolved with the maintainer, 2026-10-27)

1. **Framework = `doctest`** (not Catch2).
2. **Placement = collocated inline, each `TEST_CASE` beside the thing it tests** (not a separate
   `cpp/tests/` TU). For free functions the case sits immediately after the function; for the `Game`
   class it sits right after the class (a `TEST_CASE` can't be inside a class body). This was the
   maintainer's refinement mid-task over an initial "all tests grouped at the end of each header".

## What was done

1. **Vendored** `doctest/doctest.h` (pinned **v2.5.3**) + its `LICENSE.txt` via `tools/update-doctest.sh`
   (curl of the single header; version from the `DOCTEST_VERSION_MAJOR/MINOR/PATCH` macros) and a
   `make update-doctest DOCTEST_REF=<tag>` target — proven idempotent. `format.sh` prunes `./doctest`
   like `./imgui`.
2. **Collocated the cases** inline in `src/*.hpp`: each header `#include <doctest/doctest.h>`
   unconditionally, with `TEST_CASE`s beside the code (inside `namespace hanoi`, unqualified types).
   model (constructor / win / move_options / the move walk), presenter (label_order+change_labels,
   labelling_name, label_to_tower, labels_to_towers), recipe (Recorder, RecipeRegistry, apply same-
   labelling / through-relabel / illegal-stop, rebinding, rebound_moves, format_rebinding_table).
3. **CMake:** GUI targets get `DOCTEST_CONFIG_DISABLE` + `${CMAKE_SOURCE_DIR}` on the include path
   (the disabled header still must resolve); a native-only `hanoi-tests` executable builds
   `tests/run_tests.cpp` (the `DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN` runner) without `DISABLE`, wired
   with `enable_testing()` + `add_test()`.
4. **`make test`** (`test: image`) configures, builds only `hanoi-tests`, runs `ctest --output-on-failure`.

## Verification

`make test` nested → 1/1 ctest passed; `./hanoi-tests` reports **16 test cases / 73 assertions, 0
failed** (doctest 2.5.3). The `hanoi-cpp` GUI target rebuilds + links clean with the cases compiled
out, proving the `DISABLE` gating. clang-format run; suite re-verified after.

## Docs

`cpp/CLAUDE.md` + root `CLAUDE.md` (targets, vendored doctest pin, doctest-by-default convention);
the shared `~/.claude/reference/doctests-by-default.md` gained a `## C++` section and
`cpp-coding-standard.md` a "Tests — doctests by default" section (both sandboxes, byte-identical
mirror); the personal overlay's test-gate bullet now covers C++.
