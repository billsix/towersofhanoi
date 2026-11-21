# hanoi-gl: dataclasses, right/middle-button orbit that feels natural, thin washer discs

**Status:** in progress (go-ahead 2026-11-21)
**Priority:** 3 **Difficulty:** 3
**Created:** 2026-11-21 (William Emerison Six <billsix@gmail.com>)

## BLUF

Three changes to the Python OpenGL front-end `python/src/hanoigame/hanoigl.py`:

1. Turn its hand-written `__init__` classes into `@dataclasses.dataclass` with `__post_init__`.
2. Orbit the camera with the right or middle button only, never the left. Also research and fix why the
   rotation feels janky.
3. Replace the torus discs with thin flat discs.

Done means the gates pass (`cd python && make check-format type-check test`), `tools/gl_smoke.py` prints
`GL SMOKE OK` under Xvfb, a PPM frame shows the new discs, and the docs that describe tori or
left-drag orbiting are updated.

## Context (read first)

- Design of the GL front-end: `tasks/reference/opengl-color-id-picking.md`. Its "Moving a disc" section
  describes collision against a **torus**, and step 2 of the pick pass says a background press orbits.
  Both change here.
- The headless check is `python/tools/gl_smoke.py`. Its run recipe is in its docstring; it is not a gate.
  `drag()` aims at the tube with `major_radius(size, n)`, which is torus-specific.
- There is no parity fan-out. `hanoi-gl` is the only 3D board: the Rust and C++ GUIs draw 2D boards, and
  `tasks/reference/feature-spec.md` (the `hanoi-gl` entry in the UI list) holds no camera or disc-shape
  rules.
- Coding standard: the Python standard reference doc from github.com/billsix/runClaudeInContainer
  (`tasks/reference/python-coding-standard.md`). Annotate every binding and write Google docstrings.
  Keep the doctests.

## 1. Dataclasses with `__post_init__`

These are the candidates. The rest are already dataclasses: `MovingDisc`, `OrbitCamera`, `RebindingView`
and `PendingAction`.

- **`Mesh`**: `vertices` and `indices` become `dataclasses.InitVar`. `count`, `vao`, `vbo` and `ebo`
  become `field(init=False)`. `__post_init__` does the upload.
- **`PickBuffer`**: `width` and `height` become fields. `fbo`, `color` and `depth` become
  `field(init=False)`. `__post_init__` creates the framebuffer objects and calls `resize`.
- **`HanoiGL`**: `window` and `num_disks` become fields (`num_disks` could be an `InitVar`, since
  `session` carries it). The roughly 30 state attributes set in `__init__` become declared fields:
  - give the mutable ones `field(default_factory=…)`, e.g. `popups_to_open` defaults to
    `["How to Play"]`;
  - make the GL handles and the session `field(init=False)`, set in `__post_init__`;
  - turn the comments now beside each assignment into the class docstring's `Attributes:` section.

  Recommendation: convert it. The state list becomes declarative and documented in one place.

Use `eq=False` on all three. Field-wise `==` on GL handle integers or app state means nothing, and
`eq=False` keeps the default identity `__hash__`. Callers (`gl_smoke.py`, the `main` entry point) keep
passing the same positional arguments.

## 2. Orbit on the right or middle button only, and make it feel natural

**Buttons.**
- `press()` sets `orbiting = True` when the pick returns 0, i.e. a left press on the background. Change it
  so a left press on the background does nothing, or just sets the status line.
- In `_board_input`, start orbiting on `imgui.MouseButton_.right` (already wired) **or**
  `imgui.MouseButton_.middle`, and stop when either is released.
- A left release must still drop a carried disc. A right or middle release must not drop one. Today
  `release()` both stops orbiting and drops, so split it: `end_orbit()` for the camera buttons, and
  `release()` for the left button only.

**Feel: investigate first, then fix.** Possible causes found by reading `OrbitCamera.orbit` and
`_board_input`, to confirm or rule out before changing anything:

1. **Jumps when the cursor leaves the window.** `cursor()` uses `x - last_cursor[0]` from
   `io.mouse_pos`. When the cursor leaves the window or the window loses focus, imgui reports an invalid
   position (`-FLT_MAX`, or the `GlfwRenderer` backend's sentinel). The next delta is then huge and the
   board spins.
   - Fix: use `io.mouse_delta` and skip frames where `imgui.is_mouse_pos_valid()` is false.
   - Optional: capture the cursor while dragging.
2. **The rate ignores the window size.** `0.01` rad per pixel turns a small window slowly and a big one
   quickly. The usual rule in three.js `OrbitControls` and Blender's turntable is a full board-height drag
   ≈ 180°, i.e. `angle = π · d / board_height`, using the same height for yaw and pitch.
3. **Drag direction.** The convention is that the scene follows the hand like a lazy Susan: drag right and
   the board turns right; drag up and you look from higher. Check both signs against the view matrix in
   `_set_view_projection` (`rotate_x(pitch)`, then `rotate_y(-yaw)`). The pitch sign is the one most
   likely to feel backwards.
4. **No smoothing.** The camera follows raw per-frame deltas, so an uneven event rate shows as stutter.
   - Optional: light damping, i.e. ease the current yaw and pitch toward a target with a frame-rate-
     independent factor `1 − exp(−k·dt)`.
   - Optional: a little inertia after release.
   - Keep the pitch clamp (`0.05`–`1.45` rad).
5. **Pivot.** The view turns around the point (0, 1.2, 0), which is fine for a board on a table. Confirm
   it is the board's visual centre at every disc count. `peg_height` grows with `num_disks`.

Turntable (yaw and pitch, the vertical axis stays up) is the right model for a board on a table. An
arcball would let the board roll and is not wanted.

Update the prompts to "Drag with the right or middle button to turn the camera; the wheel zooms.":
- the How to Play text (the `imgui.text` "Drag the background (or the right button) …");
- the module docstring;
- `python/CLAUDE.md` and the reference doc.

## 3. Thin flat discs instead of tori

- Write `disc_mesh(inner_radius, outer_radius, thickness, sides=48)` next to `cylinder_mesh`. It is a
  flat-shaded ring: a top annulus, a bottom annulus, and the outer and inner walls.
  - The rims are hard edges, so duplicate the vertices there: up and down normals on the faces, radial
    normals on the walls.
  - Doctest the shape of the returned arrays, as `torus_mesh` does.
- Replace `TUBE_RADIUS` and `major_radius` with:
  - `DISC_THICKNESS`: thin, about 0.15–0.2 against today's 0.36;
  - one shared `HOLE_RADIUS`: `PEG_RADIUS` plus clearance;
  - `outer_radius(size, num_disks)`: the smallest just larger than the hole, the largest clear of the
    neighbouring stacks.
- Update `rest_y`, `carry_y`, `peg_height` and `collides_with_peg`, and fix their doctests.
  - The washer misses a peg when it is above the peg top (`y − thickness/2 ≥ peg_top`), when the peg is
    inside the hole (`distance + PEG_RADIUS ≤ HOLE_RADIUS`), or when the peg is outside the edge
    (`distance − PEG_RADIUS ≥ outer`).
- Remove `torus_mesh` once nothing uses it.
- In `gl_smoke.py`, `drag()` aims midway between the hole and the edge on the top face. Update its
  comment.
- Update every remaining "torus" mention: the module docstring, the root `CLAUDE.md` ("torus discs"),
  `python/CLAUDE.md`, the `gl` help text in `python/Makefile`, and `tasks/reference/opengl-color-id-picking.md`.

## Decisions

- **Disc shape: a flat washer with a hole for the peg** (William Emerison Six <billsix@gmail.com>,
  2026-11-21). The disc sits visibly around its peg, and the rule that a disc must clear the peg top
  before moving sideways still holds.
- **HanoiGL becomes a dataclass too**, as recommended in section 1.

## Verification

- `cd python && make check-format`, `make type-check` and `make test`, which includes the doctests.
- `tools/gl_smoke.py frame.ppm` under Xvfb, using the recipe in its docstring. Extend the smoke:
  - a left press on the background does **not** orbit;
  - a right and a middle press do;
  - a delta from an invalid mouse position does not move the camera.
- Look at the PPM to check the new disc geometry.
- On a display (the maintainer, `make gl`): the rotation feel. Add it to the existing hanoi on-display
  check rather than blocking on it.
