# hanoi-gl: full feature parity, with a Dear ImGui interface (done 2026-11-21)

**Priority:** 3 **Difficulty:** 6
**Created / done:** 2026-11-21 (William Emerison Six <billsix@gmail.com>): "for the opengl one, I like
it, but i want it to have feature parity, and I want to use imgui in python like modelviewprojection
does." Branch `hanoi-gl-imgui-parity`.

## What was done

`hanoi-gl` (`python/src/hanoigame/hanoigl.py`) now has every feature of the other GUIs, drawn with
Dear ImGui (imgui-bundle 1.93.0, modelviewprojection's pin) over the 3D board. The geometry, colour-ID
picking and disc-motion code stayed as it was; the application layer was rewritten, porting the C++
Dear ImGui app (`cpp/main.cpp`), which was already at parity:

- **Menu bar:** Game (New Game → 1–8 discs, New Game (Same Size), Quit), Relabel and Recipe dimmed until
  the first win (Recipe: Save current solution, then each recipe → View / Apply), View (Show pick buffer,
  Reset camera), Help (How to Play).
- **Game panel** (right): goal line, move count vs optimal, labels on the physical pegs when relabelled,
  valid moves, status, the six move buttons (illegal ones disabled), the move history with click-to-review
  and "Back to current", and the three-panel rebinding view as one table with selectable rows and the key
  marker.
- **Dialogs:** illegal move, save recipe (prefilled `solve-N`, overwrite reported), first-win teaching,
  save-before-discard at New Game, How to Play (every start), Continue from here?
- **Board:** pegs coloured by label with the label (and, when relabelled, the physical "peg n") drawn
  under each peg; drag and the move buttons share `HanoiGL.make_move`; review mode shows and picks from
  the reviewed board.
- `HOWTO_TEXT` moved from `hanoigui.py` to `presenter.py`, shared by both GUIs.
- `requirements.txt`: `imgui-bundle==1.93.0` (it has no other runtime dependency beyond glfw and
  PyOpenGL, already pinned; a cp315 wheel exists).
- The feature spec's compliance note, both `CLAUDE.md`s, the README and
  `tasks/reference/opengl-color-id-picking.md` (a new "imgui layer" section) describe it.

Decisions taken under the go-ahead (William Emerison Six <billsix@gmail.com>, 2026-11-21): mouse input
read from `imgui.get_io()` (GlfwRenderer owns glfw's callbacks), ignored while imgui wants the mouse; a
fixed right-hand panel with the board in the rest of the window; labels via imgui's background draw list;
the pick-buffer view moved to the View menu; How to Play not persisted, like the C++ ImGui app.

## Verification

- `make image` (nested, with the new pin); `format`, `type-check`, `test` (153 passed, 2 skipped).
- `python/tools/gl_smoke.py` under Xvfb + Mesa (GL 4.6 core): imgui frames with the menus, panel and
  dialogs; picking and a legal and an illegal drag; a move button; history review declining then
  accepting "Continue from here?"; a 1-disc win, saving its recipe, relabelling and applying it with the
  rebinding view; the pick-buffer view; no GL error. It wrote the last frame, checked by eye: panel,
  peg labels with the physical reference row, the rebinding table with the selected row and markers.
- `python/tools/gui_smoke.py` (the wx GUI, after the `HOWTO_TEXT` move): `SMOKE OK 2`.
- Not checked: a real display (hardware GL, HiDPI scaling, the feel of the drag). That is the
  maintainer's `make gl` check.
