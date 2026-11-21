# Python OpenGL 3.3 3D board: torus discs, orbit camera, color-ID picking, discs slide up the peg

**Status:** proposed — needs go-ahead (decisions recorded 2026-11-21; no open questions)
**Priority:** 5
**Difficulty:** 7
**Created:** 2026-11-21 (William Emerison Six <billsix@gmail.com>)

## BLUF

Write a 3D hanoi front-end in Python on **OpenGL 3.3 core**: discs are tori (generated in code, or
exported from Blender), pegs are cylinders, and the camera orbits in 3D the way modelviewprojection's
demos do. Selection uses **color-ID picking**: on mouse-down, render the scene once into an
offscreen framebuffer object (never shown on screen) with each pickable object drawn in a flat color
that encodes its ID, read the pixel under the cursor with `glReadPixels`, decode the ID, then render
the normal frame. A picked disc animates **up its peg until it clears the top**, follows the drag,
and drops onto the target peg with **collision detection** (it cannot pass through pegs or other
discs). The code is written so it can be lifted into modelviewprojection later to teach selection.
Done = a runnable `make` target in `python/`, moves dispatched through the shared engine, and the
picking code clear enough to teach from.

## Context

- Read first: `CLAUDE.md`, `python/CLAUDE.md`, `tasks/reference/ui-design-principles.md` ruling #7
  (drag-and-drop: nearest-peg targeting, illegal drop snaps back, dragging off once solved),
  `tasks/reference/feature-spec.md` §7 (the compliance checklist a new UI must meet, or say which
  rows it skips).
- **The later destination is modelviewprojection** (github.com/billsix/modelviewprojection). It uses
  `glfw`, PyOpenGL and `gacalc[gl]` (its `requirements.txt`). Using the same stack and
  coordinate-frame style makes the port to it a copy, not a rewrite (Decisions: same stack).
- Keep the front-end thin: a drop becomes a `<from>→<to>` move through `engine.dispatch` /
  `commands.parse`, as the wx drag does (`python/src/hanoigame/hanoigui.py` `_on_board_drop`).
- Picking, as the maintainer specified it:
  1. Mouse-down → bind an FBO (color attachment + depth renderbuffer, same size as the window).
  2. Draw every pickable object with a flat-color shader whose color is its ID (e.g. ID in the RGB
     bytes, 0 = background); no lighting, no blending, no multisampling on that target.
  3. `glReadPixels` the one pixel under the cursor (flip y), decode the ID.
  4. Unbind the FBO and draw the real frame, now knowing what was selected.
  Pickable: the **top** disc of each peg (others ignored, or picked but rejected with the usual
  message); pegs are not pickable (Decisions).
- Disc motion: lift along the peg's axis until the disc's hole clears the peg top, then move with the
  cursor in a plane above the pegs, then lower onto the target peg. Collision: the lifted disc must
  not intersect a peg or another stack while moving (bounding cylinders are enough); the drop target
  is the nearest peg, and an illegal target snaps the disc back down its source peg.
- New dependencies go in `python/requirements.txt` + `make update-pins` (pinned, per the repo's
  Python-deps rules); a GL app needs the image's GUI passthrough
  (`tasks/archive/2026/09/16/enable-gui-wayland-x-passthrough.md`) and GL drivers. **The Python
  image ships no OpenGL/Mesa today** (root `CLAUDE.md`: "`USE_X_WINDOWS` … no OpenGL/mesa"), so this
  adds a permanent image dependency (Mesa + `glfw`), which needs the maintainer's yes; it comes with
  the go-ahead for this task.

## Plan (rungs, each runnable)

1. Window + GL 3.3 core context, one shaded torus, orbit camera (mouse drag rotates, wheel zooms).
2. The full board (three pegs, base, *n* tori) from the engine's game state.
3. The picking pass: FBO + ID shader + `glReadPixels`; print the picked ID. A debug key shows the ID
   buffer on screen (teaching aid).
4. Lift-and-drag animation with collision; drop → engine move; snap back on illegal.
5. Status text (move count, legal/illegal reason), win detection, dragging off once solved.
6. A `make gl` target, a headless smoke test if feasible (Xvfb + Mesa llvmpipe supports 3.3 core),
   and a short reference note on the picking design for the modelviewprojection port.

## Decisions (William Emerison Six <billsix@gmail.com>, 2026-11-21: "go with your recommendations")

- **Stack: `glfw` + PyOpenGL**, as modelviewprojection uses, so the port to it is a copy.
- **Tori are generated in code** (parametric torus → vertex/normal/index buffers); no Blender assets.
- **Only discs get pick IDs;** the drop target is the nearest peg by position (ruling #7).
- **Transforms use gacalc,** as modelviewprojection does.
- The Mesa + `glfw` image dependency is accepted with these decisions.
