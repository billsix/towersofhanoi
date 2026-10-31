# Fix uneven peg spacing in the C++ ImGui board

**Status:** proposed — investigate root cause, then fix; needs go-ahead to start.
**Priority:** 3
**Difficulty:** 3

## BLUF

The three pegs render with **uneven spacing** in the **C++ Dear ImGui board** (`cpp/main.cpp`,
draw-list primitives). Find the root cause (a layout-math bug in how peg x-positions are computed) and
make the pegs **evenly spaced**. Verify headless, then the maintainer's on-display check.

## Context (cold-start orientation)

- **Target (confirmed by the maintainer 2026-10-31):** "whatever the ImGui one or ones were." ImGui is
  **C++ only** — `cpp/main.cpp` — and the native + WebAssembly builds come from that one source, so one
  fix covers both. (There is no Python ImGui build; Python's graphical GUI is wxPython, not a target
  unless step 1 finds it shares the bug.)
- **Also glance (report, don't fix unless asked):** while reproducing, look at the other graphical
  boards (Rust egui, the wx boards, the Python wxPython board) and note whether any share the uneven
  spacing — flag it so the maintainer can decide, but the named target is the ImGui board.
- **Likely cause (hypothesis, verify — don't inherit):** peg x-positions computed by dividing the
  board width without symmetric margins, or an off-by-one (`i * w/3` vs `(i+0.5) * w/3`), or integer
  rounding that accumulates — so the gaps between pegs and to the edges differ. The fix is centered
  thirds / equal gaps.

## Plan

1. **Reproduce:** run the ImGui board (headless where possible — see
   `tasks/reference/imgui-cpp-native-and-wasm.md` for the C++ headless path) and record the uneven
   spacing. Glance at the other boards and note any that share it.
2. **Root-cause:** read the peg-layout math in `cpp/main.cpp`. State the actual bug, don't guess.
3. **Fix:** even spacing — equal left/right margins and equal inter-peg gaps, robust to disk width and
   window size. Keep the renderer's existing style otherwise.
4. **Verify:** headless screenshot shows equal gaps; `cd cpp && make build && make test` stays green;
   maintainer's on-display `make gui` run is the last check.

## Related

- `cpp/main.cpp` (the C++ ImGui board), `tasks/reference/imgui-cpp-native-and-wasm.md` (build/run +
  headless path), `tasks/reference/feature-spec.md` §5 (the board is a mandatory shown element).
