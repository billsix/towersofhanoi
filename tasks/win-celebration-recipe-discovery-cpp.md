# Win celebration + recipe discovery — C++

**Status:** proposed — needs go-ahead.
**Priority:** 5 **Difficulty:** 5
**Part of:** `tasks/win-celebration-recipe-discovery.md` (umbrella — the cross-cutting design + the four
open questions that **block implementation**).
**Depends on:** `tasks/win-celebration-recipe-discovery-python.md` (mirror the oracle's wording + the spec
update; don't invent wording).
**Created:** 2026-11-01 (William Emerison Six <billsix@gmail.com>).

## BLUF

Mirror the Python win-celebration wording into the C++ **header-only core** (`cpp/src/`), then wire both
GUIs to surface it at the win: `cpp/main.cpp` (Dear ImGui — **native SDL2+OpenGL3 and WebAssembly**) and
`cpp/hanoiwx.cpp` (wxWidgets, `make wx`). "Done" = both GUIs show the first-win teaching moment + lighter
later wins, wording matches the oracle (a `doctest` `TEST_CASE` asserts it), the build + `ctest` pass
(native, wasm, wx), and the maintainer display-verifies.

## Context (read first)

- Umbrella design + open questions: `tasks/win-celebration-recipe-discovery.md`. Wording is the **Python
  task's output** — reproduce it.
- C++ layering + GUIs: `tasks/reference/imgui-cpp-native-and-wasm.md` and `cpp/CLAUDE.md`. The engine is
  header-only in `cpp/src/`; put the celebration-text helper there (free function / presenter header) so
  both GUIs share it. Tests are **doctest** `TEST_CASE`s compiled out of the GUI binaries with
  `-DDOCTEST_CONFIG_DISABLE`, run under `ctest` from `make test` (`~/.claude/reference/doctests-by-default.md`).
- Both GUIs already gate Tier-2 and are at feature-spec parity (feature-spec.md §"Other implementations");
  this adds the explicit win moment on top of the existing menu-enable.

## Plan

1. **Core helper** in `cpp/src/` (a `format_win_celebration(...)` free function / presenter header): the
   mirror of the Python wording, with a `doctest` `TEST_CASE` asserting the exact oracle strings.
2. **ImGui GUI** (`main.cpp`): on first win, a one-time **modal** (`OpenPopup`/`BeginPopupModal`) with the
   celebration text and — per umbrella Q2 — a **Save as recipe** action prefilled `solve-<N>`; lighter
   inline line on later wins. Must work **native and wasm** (no desktop-only calls on the popup path).
3. **wxWidgets GUI** (`hanoiwx.cpp`): a native modal on first win (Save prefilled `solve-<N>`), lighter
   after. Shares the core helper with ImGui.
4. **Verify:** the C++ build + `ctest` (native ImGui, **wasm build**, wx) green via `make` targets;
   maintainer runs the GUIs on display (native + browser for wasm).

## Open questions — resolved

- The umbrella's four are **resolved** (2026-11-01; see umbrella): teaching first-win-only; congrats +
  Save offer every win; shared core helper; spec updated (by the Python task). **C++-local:** none beyond
  the ImGui wasm constraint (keep the popup path free of native-only APIs) — implementation discretion.

## Related

- Umbrella + Python oracle: `tasks/win-celebration-recipe-discovery.md`,
  `tasks/win-celebration-recipe-discovery-python.md`.
- `tasks/reference/imgui-cpp-native-and-wasm.md`, `cpp/CLAUDE.md`, `tasks/reference/feature-spec.md`.
