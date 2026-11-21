# hanoi-gl: full feature parity, with a Dear ImGui interface like modelviewprojection's

**Status:** in progress
**Priority:** 3
**Difficulty:** 6
**Created:** 2026-11-21 (William Emerison Six <billsix@gmail.com>): "for the opengl one, I like it, but
i want it to have feature parity, and I want to use imgui in python like modelviewprojection does."

## BLUF

The Python 3D front-end `hanoi-gl` (`python/src/hanoigame/hanoigl.py`) plays the game but skips most of
the feature spec. Give it everything the other GUIs have (relabelling, recipes with the three-panel
rebinding view, the always-visible move history with review, move buttons, valid moves, the learning-flow
tiers, How to Play, win celebration, save-before-discard), drawn with **Dear ImGui through imgui-bundle**
over the 3D board, the way github.com/billsix/modelviewprojection's demos do. Done = every row of the
feature spec's compliance checklist (`tasks/reference/feature-spec.md` §7) holds for `hanoi-gl`, the
compliance note in that spec says so, and the Python gates plus a headless smoke pass.

## Context

- Read first: `tasks/reference/feature-spec.md` (§4 features, §6.2 GUI advice, §7 checklist, and the
  "Python `hanoi-gl`" compliance note this task replaces), `tasks/reference/ui-design-principles.md`,
  `tasks/reference/opengl-color-id-picking.md` (the picking and disc-motion design, kept as it is).
- **The template is the C++ Dear ImGui app** (`cpp/main.cpp`), already at full parity: its menu bar
  (Game / Relabel / Recipe / Help, Tier-2 gating with `BeginDisabled`), modals (save recipe, first-win,
  save-before-discard, How to Play, illegal move, continue-from-here), the three-panel table with linked
  rows, move buttons, and history with review are ported to Python imgui-bundle calls.
- **How modelviewprojection uses imgui** (read 2026-11-21 in its `src/modelviewprojection/demos/demo21/
  demo21.py` and `requirements.txt`): `imgui-bundle[glfw]==1.93.0`; `import glfw` **before**
  `imgui_bundle` (so the standard glfw is the one loaded); `imgui.create_context()`, then
  `GlfwRenderer(window)` from `imgui_bundle.python_backends.glfw_backend`; each frame
  `impl.process_inputs()`, `imgui.new_frame()`, the UI, the GL scene, `imgui.render()`,
  `impl.render(imgui.get_draw_data())`. In the container the Makefile sets
  `PYGLFW_LIBRARY=/usr/lib64/libglfw.so.3` (geometricalgebra's `tasks/reference/gl-toolkit.md` explains
  why imgui_bundle needs the dual X11/Wayland build); `make gl` already does.
- Engine API it uses: `GameSession.dispatch` (Move, Relabel, Apply, Show), `save_recipe`,
  `valid_moves_str`, `state_after` / `truncate_to` (history review), `RecipeRegistry`,
  `presenter.format_win_celebration`, `default_recipe_name`, `format_move_tally`, `recipe.rebinding` /
  `rebound_moves`.

## Decisions (made under the go-ahead, William Emerison Six <billsix@gmail.com>, 2026-11-21: "implement it")

1. **Mouse input comes from imgui's IO, not extra glfw callbacks.** `GlfwRenderer` installs its own
   callbacks; the board reads `imgui.get_io()` each frame (`is_mouse_clicked`, `mouse_pos`, wheel) and
   ignores the mouse whenever `io.want_capture_mouse` (a window or menu is under it).
2. **Layout:** the 3D board fills the window under the menu bar, left of a fixed right-hand "Game" panel
   (goal line, status, valid moves, the six move buttons, the move history with "Back to current", and
   the rebinding view). The GL viewport, picking and the cursor ray use the board's rectangle only.
3. **Labels in 3D:** pegs are coloured by label (blue, gold, red, as the other GUIs), and each peg's
   label number is drawn under it with the imgui background draw list (projected from the peg's base),
   plus the physical "peg n" reference row when relabelled (feature-spec §4.3).
4. **Shared text moves to the core:** `HOWTO_TEXT` moves from `hanoigui.py` to `presenter.py` so both GUIs
   use one copy without `hanoi-gl` importing wx.
5. **"Show pick buffer"** moves from the `P` key to a View menu item (the key stays).
6. The How to Play "don't show again" preference is not persisted (no config store here); it shows on
   first frame of each run, as the C++ ImGui app does.

## Plan

1. `requirements.txt`: `imgui-bundle==1.93.0` plus its resolved dependencies, pinned.
2. Move `HOWTO_TEXT` to `presenter.py`.
3. Rewrite the `hanoigl.py` application layer on imgui (keep the geometry, picking and motion code).
4. `tools/gl_smoke.py`: also drive relabel, a recipe save + apply, history review, and one imgui frame.
5. Feature spec compliance note, `python/CLAUDE.md`, root `CLAUDE.md`, README, the picking reference doc.
6. Gates: `make image` (new pins), `format`, `type-check`, `test`; the smokes under Xvfb; a rendered frame
   checked by eye.
