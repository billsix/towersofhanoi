# hanoi-gl: dataclasses, right/middle-button orbit that feels natural, thin washer discs

**Created:** 2026-11-21 (William Emerison Six <billsix@gmail.com>). **Done:** 2026-11-21.

Three changes to the Python OpenGL front-end, `python/src/hanoigame/hanoigl.py`. The camera and disc
design now lives in `tasks/reference/opengl-color-id-picking.md` ("The camera", "Moving a disc").

## What was done

- **Dataclasses.** `Mesh`, `PickBuffer` and `HanoiGL` became `@dataclasses.dataclass(eq=False)`, each
  with a `__post_init__` that builds its GL objects.
  - `eq=False` because field-wise `==` on GL handles or app state means nothing, and it keeps the
    identity hash.
  - `Mesh` takes its vertices and indices as `InitVar`s, so they are uploaded and not kept.
  - `HanoiGL` takes `num_disks` as an `InitVar`; the session keeps the count.
  - Its roughly 30 state attributes are declared fields. Mutable defaults use `default_factory`. The GL
    handles and the session are `init=False`. The comments beside the old assignments moved into the
    `Attributes:` docstring.
  - The callers did not change: `HanoiGL(window)`, `HanoiGL(window, num_disks=3)`, `Mesh(*disc_mesh(…))`,
    `PickBuffer(1, 1)`.
- **Camera buttons.** The right or middle button turns the camera (`start_orbit` / `orbit_to` /
  `end_orbit`). A left press on the background no longer orbits; it sets the status line to "Drag with
  the right or middle button to turn the camera." `release()` only drops a disc now. The How to Play
  text, module docstring and docs were updated.
- **Camera feel.** The investigation confirmed four of the five suspected causes:
  1. **Focus-loss spin: confirmed.**
     - imgui-bundle 1.93.0's `GlfwRenderer.mouse_callback` reports the cursor as (-1, -1) when the window
       is unfocused. imgui counts that as a valid position, so `io.mouse_delta` carries the jump too.
     - `orbit_to` treats (-1, -1) and imgui's invalid position as unusable and restarts the drag from the
       next real one, instead of turning by the jump.
  2. **Pixel-fixed rate: confirmed.** The rate was 0.01 rad per pixel. It is now π per board height, in
     logical pixels.
     - three.js `OrbitControls` uses 2π per height; π was chosen as calmer for a board that tilts through
       only 80°.
  3. **Yaw direction: confirmed backwards.** A drag right turned the board's near side left. The view now
     uses `rotate_y(+yaw)`. The pitch direction was already right: drag down, look from higher, as in
     `OrbitControls`. Both are asserted in `tools/gl_smoke.py` by projecting a near point before and after
     a drag.
  4. **No smoothing: added.** `OrbitCamera.follow(dt)` eases the shown angles toward `target_yaw` and
     `target_pitch` by `1 − exp(−25·dt)` per frame, frame-rate independent (about 92% done after 0.1 s).
     There is no inertia.
  5. **Fixed pivot: changed.** The pivot was fixed at y = 1.2, above the middle of a 3-disc scene. It is
     now half of `carry_y(num_disks)`, the middle of the scene from the base to a carried disc.
- **Washer discs.** `disc_mesh(inner, outer, thickness)` replaced `torus_mesh`. It builds four bands: the
  top and bottom faces and the outer and inner walls, each band with its own vertices so the rims are
  hard edges.
  - `TUBE_RADIUS` and `major_radius` were replaced by `DISC_THICKNESS` = 0.2 (the torus was 0.36 thick),
    one `HOLE_RADIUS` = peg radius + 0.06, and `outer_radius(size, n)` (0.48 to 1.45).
  - `rest_y`, `peg_height`, `carry_y` and `collides_with_peg` use them.
  - The shape decision is a washer with a hole, not a solid disc (William Emerison Six
    <billsix@gmail.com>, 2026-11-21). The disc sits around its peg, and the rule that a disc must clear
    the peg top before moving sideways still holds.
  - `gl_smoke.py` aims at the top face, midway between the hole and the edge.

## Verification

- `cd python && make format`, `make type-check` and `make test` all pass: 155 passed, 2 skipped, with new
  doctests for `disc_mesh`, `outer_radius`, `OrbitCamera.orbit` and `OrbitCamera.follow`.
- `tools/gl_smoke.py` printed `GL SMOKE OK` under Xvfb + Mesa llvmpipe. It now also checks:
  - a left press on the background does not orbit;
  - a right drag turns the board's near side right and tilts it down;
  - (-1, -1) and invalid positions do not move the camera.
- A frame captured as a PPM showed the washers with their holes around the pegs.
- Not checked here: how the rotation feels on a real display (`make gl`). That stays part of the
  maintainer's hanoi on-display check.
