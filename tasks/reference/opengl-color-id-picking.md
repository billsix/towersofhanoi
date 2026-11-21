# Colour-ID picking in `hanoi-gl` — how selection works, and how to port it

**Reference document.** States how the Python 3D front-end (`python/src/hanoigame/hanoigl.py`, `make gl`;
a Dear ImGui interface over the 3D board, at full feature parity) selects a disc under the mouse, how a picked disc moves, and what to carry over when the picking lesson
moves into github.com/billsix/modelviewprojection. Written 2026-11-21 (William Emerison Six
<billsix@gmail.com>) from `tasks/archive/2026/11/21/python-opengl33-3d-board-with-picking.md`.

## Picking, in three steps (`HanoiGL.pick_at`)

1. **Draw the scene again, offscreen.** `PickBuffer` is a framebuffer object with an RGBA8 colour
   renderbuffer and a 24-bit depth renderbuffer, the size of the window's framebuffer. It is never shown.
   The pick program (`PICK_VERTEX_SHADER` / `PICK_FRAGMENT_SHADER`) has no lighting and no blending: each
   object is one flat colour, `id_to_rgb(object_id)`, the ID's low/middle/high bytes as red/green/blue.
   Discs get their size as ID; pegs and the base get ID 0 and are still drawn, so depth testing lets them
   hide discs behind them. Without that, a click on a peg in front of a disc would pick the disc.
2. **Read one pixel.** Window coordinates are scaled to framebuffer pixels (they differ on HiDPI screens)
   and y is flipped (GL rows count from the bottom); `glReadPixels` reads that one RGBA pixel, and
   `rgb_bytes_to_id` decodes it. 0 means background: the press orbits the camera instead.
3. **Draw the real frame.** The window's framebuffer was never touched; the next `draw` is the lit scene.

View → Show pick buffer (or `P`) draws the pick pass to the board instead (IDs multiplied by a `brightness` uniform, since 1/255 is
black to the eye); the real pick always uses brightness 1, so the colours stay exact.

## Moving a disc (`MovingDisc.advance`)

Phases `LIFTING` → `CARRYING` → `LOWERING`. A sideways step is taken only if `collides_with_any_peg` says
the disc at its new position would not intersect a peg's cylinder (a torus misses a peg when it is above
the peg top, when the peg passes wholly through its hole, or when the peg is wholly outside its edge). So
a disc has to rise above the peg top before it can leave, and the carry height `carry_y` keeps it above
every peg. On release the target is the nearest peg; an illegal target (larger on smaller) becomes the
source, with the reason in the title. The disc lowers along the target peg until it rests on the top
disc (`rest_y` of the stack height). Only on landing is the move dispatched through
`engine.GameSession.dispatch`, so the engine stays the single place the rules live.

## The imgui layer (`HanoiGL.frame`)

- Set up as modelviewprojection's demos do: `import glfw` before `imgui_bundle`, `imgui.create_context()`,
  `GlfwRenderer(window)`; each frame `process_inputs()`, `imgui.new_frame()`, the UI, the 3D board,
  `imgui.render()`, `renderer.render(imgui.get_draw_data())`.
- `GlfwRenderer` takes over glfw's input callbacks, so the board reads the mouse from `imgui.get_io()`
  each frame and ignores it while `io.want_capture_mouse` is set (a menu, the panel or a dialog is
  under it).
- The board fills the window under the menu bar, left of the fixed Game panel; the GL viewport, the
  pick framebuffer, the cursor ray and the label projection all use that rectangle
  (`HanoiGL._board_rect`), in framebuffer pixels.
- Peg labels are text on imgui's background draw list, placed by projecting each peg's base: drawn
  after the scene and under the imgui windows.
- ImGui's built-in font is ASCII-only, so shared text goes through `ascii_text` (an arrow or a dash
  would show as "?") and the rebinding key marks with `>`.
- imgui leaves scissoring on and blending set, so `draw_board` resets the state it needs each frame.

## Porting to modelviewprojection

- **Same stack:** glfw, PyOpenGL, and `gacalc.gl.matrix_stack` (only `numpy`; `import gacalc` also pulls
  sympy). modelviewprojection's demos use the same stack and the same `glUniformMatrix4fv(…, GL_TRUE, …)`
  upload of row-major matrices.
- **Self-contained pieces:** `id_to_rgb` / `rgb_bytes_to_id`, `PickBuffer`, the two pick shaders and
  `pick_at` carry over as they are; `_scene()` is the hanoi-specific list of (mesh, position, colour, ID).
- **Gotchas found while building it:**
  - `shaders.compileProgram(..., validate=False)`: validation needs a bound VAO in a core profile and
    fails on some drivers (macOS) before any VAO exists.
  - `ty` cannot see an `|` on PyOpenGL constants (`glClear` masks need a narrow `ty: ignore`), and glfw's
    window type is the private `_GLFWwindowPointerT`, aliased under `TYPE_CHECKING`.
  - In the container, set `PYGLFW_LIBRARY=/usr/lib64/libglfw.so.3` (the `make gl` target does), as
    geometricalgebra's `tasks/reference/gl-toolkit.md` explains for Wayland.
- **Headless check:** `python/tools/gl_smoke.py` under Xvfb + Mesa llvmpipe (reports GL 4.6 core) drives
  a pick, a legal drag and an illegal one. For pictures, read the back buffer with `glReadPixels`; a
  screenshot of an llvmpipe window is black.
