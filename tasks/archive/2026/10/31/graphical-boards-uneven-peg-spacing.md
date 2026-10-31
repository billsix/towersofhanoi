# Fix uneven peg spacing in the C++ ImGui board

**Status:** DONE 2026-10-31 (fix on branch `ui-learning-flow-and-fixes`).
**Priority:** 3
**Difficulty:** 3

## Work record / findings (DONE 2026-10-31)

- **Root cause (verified in the code, not inherited):** the three peg **centres** are evenly spaced in
  *every* graphical board — egui (`rust/hanoi-egui/src/main.rs:285-293`) and wxPython
  (`python/src/hanoigame/board_renderers.py:260-274`) share the formula
  `centre = left + margin + (avail_w/3)*(i+0.5)` with `avail_w = w − 2·margin` (margin 20px). The
  **C++ ImGui board** (`cpp/main.cpp` `draw_board`) alone used `peg_gap = board_w/3`,
  `cx = origin.x + peg_gap*(i+0.5)` — centres at 1/6, 1/2, 5/6 of the **full** width with **no edge
  margin**, so the outer pegs and the widest bottom discs hugged the board edges. That edge-crowding
  is the "uneven" look; the centre spacing itself was never wrong.
- **Fix:** gave the ImGui board the same inset layout (margin 20px; `avail_w = board_w − 2·margin`;
  `peg_gap = avail_w/3`; `cx = origin.x + margin + peg_gap*(i+0.5)`), so the outer pegs clear the edges
  and all three graphical boards share one peg layout (the Consistency principle). Commit on the branch.
- **The other boards left as-is (report-only, per the maintainer's decision):** egui and wxPython were
  already correctly inset; no change. ("The python one" in the original request is the wxPython Cairo
  board — already even.)
- **Verification:** `cd cpp && make build` (hanoi-cpp + hanoi-wx + hanoi-tests compile) + `make test`
  (ctest) green; clang-format clean. No headless screenshot path exists for the ImGui board, so the
  spacing was reasoned from the (now-unified) layout math; the maintainer's on-display `make gui` is
  the final visual check.
- **Tooling note (for the session report):** `make -o image format` ran the image's **stale baked**
  `/format.sh` (predating the `./doctest` prune now in `entrypoint/format.sh`) and reformatted the
  vendored `cpp/doctest/doctest.h`; restored it and re-verified with the mounted current script. A
  fresh image (the maintainer's CI) uses the current script and is unaffected.

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
