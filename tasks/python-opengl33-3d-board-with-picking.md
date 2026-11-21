# Python OpenGL 3.3 3D board with colour-ID picking (done 2026-11-21)

**Priority:** 5 **Difficulty:** 7
**Created / done:** 2026-11-21 (William Emerison Six <billsix@gmail.com>); branch `gui-batch-2026-11-21`.

## What was done

A fourth Python front-end, `hanoi-gl` (`python/src/hanoigame/hanoigl.py`, `make gl`): a 3D board in an
OpenGL 3.3 core window. Discs are tori and pegs cylinders, generated in code; an orbit camera turns
around the board (drag the background or use the right button; the wheel zooms). Selection is
**colour-ID picking**: on mouse-down the scene is drawn into an offscreen framebuffer with each disc in a
flat colour that encodes its ID, the pixel under the cursor is read back and decoded, then the normal
frame is drawn. A picked top disc slides up its peg until it clears the top, follows the cursor, and on
release comes down on the nearest peg; collision checks keep it from passing through a peg, and an
illegal drop slides back home. Moves go through `engine.GameSession.dispatch`. `P` shows the ID buffer,
`1`–`8` start a new game, `R` resets the camera. How it works and how to port it:
`tasks/reference/opengl-color-id-picking.md`.

Decisions (William Emerison Six <billsix@gmail.com>, 2026-11-21, "go with your recommendations"):
glfw + PyOpenGL like modelviewprojection (not a wx GL canvas); tori generated in code (no Blender assets);
only discs are pickable, the target is the nearest peg by position; transforms through gacalc's matrix
stack (`gacalc.gl.matrix_stack`, which needs only numpy, so not the `gl` extra). The Mesa + glfw image
dependency was accepted with these decisions.

It is a teaching piece for picking, not a full-feature UI: it has play, win detection and the move count
vs optimal (in the window title), and skips labellings, recipes, the rebinding view and the move history.
The feature spec's compliance section records this.

### Build and image changes (`python/`)

- `requirements.txt`: `gacalc==0.1.1`, `glfw==2.11.0`, `numpy==2.5.4`, `PyOpenGL==3.1.10`,
  `sympy==1.14.0`, `mpmath==1.3.0` (the versions modelviewprojection pins).
- `entrypoint/05-install-gl.sh` (glfw, Mesa GL/EGL and drivers, the X11/Wayland libs GLFW loads), run
  in its own Dockerfile layer under `USE_X_WINDOWS`; the list matches geometricalgebra's
  `entrypoint/07-install-gl.sh`.
- `make gl`: passes `/dev/dri` when present and sets `PYGLFW_LIBRARY=/usr/lib64/libglfw.so.3`.
- `entrypoint/type-check.sh` passes the interpreter's site-packages to ty with `--extra-search-path`:
  uv installs the pip set under `/usr/local`, which ty does not search by default, so the new imports
  failed to resolve.
- `pyproject.toml`: the `hanoi-gl` script; `tools/gl_smoke.py` allowed to print its pass line (T201).
- Root and `python/` `CLAUDE.md` describe the new front-end and no longer say the image has no OpenGL.

## Verification

- `make image` rebuilt nested (the new GL layer + pip set); `format`, `type-check`, `test` (152 passed,
  2 skipped, including the module's doctests for the layout, collision and ID-encoding functions, the
  mesh builders and `MovingDisc.advance`) green.
- `python/tools/gl_smoke.py` under Xvfb + Mesa (GL 4.6 core profile): a click on empty space picks ID 0;
  disc 1 dragged to peg 3 lands and the engine records `(1, 3)`; disc 2 dropped on disc 1 slides home
  with "larger on smaller"; both draw paths run without a GL error. `tools/gui_smoke.py` still passes.
- The lit frame and the ID buffer were read back with `glReadPixels` and checked by eye (a one-shot
  script, `tasks/adhoc/python-opengl33-3d-board-with-picking/frame_png.py`, removed at archive): the
  discs, pegs and base render lit, and in the ID buffer the pegs hide the discs behind them.
- Not checked: the feel on a real display (camera, drag speed, hardware GL). That is the maintainer's
  `make gl` check.
