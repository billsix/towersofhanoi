# Fix uneven peg spacing in the graphical boards

**Status:** proposed — investigate root cause, then fix; needs go-ahead to start.
**Priority:** 3
**Difficulty:** 3

## BLUF

The three pegs render with **uneven spacing** in at least two graphical boards. Find the root cause
(a layout-math bug in how peg x-positions are computed) and make the pegs **evenly spaced**. Verify by
headless render/screenshot where possible, then the maintainer's on-display check.

## Context (cold-start orientation)

- **Which builds (CONFIRM — naming ambiguity):** the maintainer said "the IMGUI python one, and C++
  one". There is **no Python ImGui build** — Python's graphical GUI is **wxPython** (a `wx.GraphicsContext`
  / Cairo 2D board in `python/src/hanoigame/board_renderers.py`); **ImGui is C++ only**
  (`cpp/main.cpp`, draw-list primitives). Working interpretation: fix **(a) the Python wxPython
  graphics board** and **(b) the C++ ImGui board**. First step of the investigation is to **observe
  each graphical board and confirm which actually show uneven spacing** (also glance at Rust egui and
  the wx boards, since they may share the bug) — correct the target list before fixing.
- **Likely cause (hypothesis, verify — don't inherit):** peg x-positions computed by dividing the
  board width without symmetric margins, or an off-by-one (`i * w/3` vs `(i+0.5) * w/3`), or integer
  rounding that accumulates — so the gaps between pegs and to the edges differ. The fix is centered
  thirds / equal gaps, applied per renderer.

## Plan

1. **Reproduce + confirm targets:** run each graphical board (headless where possible — `cpp/` has a
   headless path; wxPython via the project's X/Xvfb route) and record which show uneven spacing and by
   how much. Narrow to the real offenders.
2. **Root-cause each offender:** read the peg-layout math in the affected renderer(s)
   (`board_renderers.py` for wxPython; the draw-list layout in `cpp/main.cpp` for ImGui). State the
   actual bug, don't guess.
3. **Fix:** even spacing — equal left/right margins and equal inter-peg gaps, robust to the disk
   width and window size. Keep each renderer's existing style otherwise.
4. **Verify:** headless screenshot shows equal gaps; `cd <sub> && make test` / `make build` stays
   green; maintainer's on-display run is the last check.

## Open questions (answer by number)

1. **Confirm the targets** — is "the IMGUI python one" the **wxPython** graphics board (my reading), or
   did you mean a different build? And should I fix the same bug in the Rust egui / wx boards if they
   share it, or only the two you named? (Rec: fix every graphical board that shows it — one consistent
   layout.)

## Related

- `python/src/hanoigame/board_renderers.py` (wxPython 2D board), `cpp/main.cpp` (C++ ImGui board).
- `tasks/reference/feature-spec.md` §5 (the board is a mandatory shown element),
  `tasks/reference/imgui-cpp-native-and-wasm.md` (C++ ImGui build/run + headless path).
