"""Headless smoke for the OpenGL 3D front-end (hanoi-gl): picking + moving.

A manual, display-dependent check that the format/type-check/test gates can't
reach -- NOT wired into any gate (it needs an X display with OpenGL 3.3; Mesa's
llvmpipe in Xvfb is enough). Run it from the Python subproject:

    cd python
    podman run --rm --entrypoint /bin/bash \
      -v "$PWD":/hanoi-python:Z hanoi-python \
      -c 'dnf install -y xorg-x11-server-Xvfb >/dev/null 2>&1; \
          cd /hanoi-python && xvfb-run -a -s "-screen 0 1280x800x24" \
          python tools/gl_smoke.py'

Prints "GL SMOKE OK" on success. It picks the top disc through the offscreen
colour-ID pass, drags it to peg 3 (lift, carry, lower) and checks the engine
recorded the move; tries an illegal drop and checks the disc went home; and
checks that a click on empty space picks nothing.
"""

import gacalc.gl.matrix_stack as ms
import glfw
import numpy as np
import OpenGL.GL as GL
from numpy.typing import NDArray

from hanoigame.hanoigl import (
    HanoiGL,
    major_radius,
    peg_x,
    rest_y,
)


def screen_point(
    app: HanoiGL, x: float, y: float, z: float
) -> tuple[float, float]:
    """Project world point (x, y, z) into window coordinates."""
    app._set_view_projection()
    mvp: NDArray[np.float32] = ms.get_current_matrix(
        ms.MatrixStack.modelviewprojection
    )
    clip: NDArray[np.float32] = mvp @ np.array([x, y, z, 1.0])
    ndc: NDArray[np.float32] = clip[:3] / clip[3]
    width: int
    height: int
    width, height = glfw.get_window_size(app.window)
    return (ndc[0] + 1.0) / 2.0 * width, (1.0 - ndc[1]) / 2.0 * height


def drag(app: HanoiGL, size: int, from_peg: int, to_peg: int) -> None:
    """Press on disc `size` (on top of `from_peg`), carry it over `to_peg`,
    release, and run frames until it lands."""
    n: int = app.session.num_disks
    index: int = len(app.session.game.towers[from_peg]) - 1
    # The torus centre is its hole, so aim at the tube on the near-right side.
    grab: tuple[float, float] = screen_point(
        app, peg_x(from_peg) + major_radius(size, n), rest_y(index), 0.0
    )
    app.press(*grab)
    assert app.moving is not None, f"disc {size} not picked: {app.message}"
    assert app.moving.size == size, app.moving
    frame: int
    for frame in range(400):
        app.update(1 / 60)
        if frame == 100:  # lifted by now: steer over the target peg
            app.cursor(*screen_point(app, peg_x(to_peg), 3.0, 0.0))
    app.release()
    for _frame in range(400):
        app.update(1 / 60)
    assert app.moving is None, app.moving


assert glfw.init(), "glfw.init failed"
glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL.GL_TRUE)
glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
window: object = glfw.create_window(1000, 700, "gl smoke", None, None)
assert window, "no OpenGL 3.3 core window"
glfw.make_context_current(window)
print("GL_VERSION", GL.glGetString(GL.GL_VERSION).decode())
app: HanoiGL = HanoiGL(window, num_disks=3)

# A click above the board hits only the background clear colour: ID 0.
assert app.pick_at(5.0, 5.0) == 0

# Smallest disc 1 -> 3: lifted, carried, lowered, and recorded by the engine.
drag(app, size=1, from_peg=0, to_peg=2)
assert app.session.recorder.default_moves == [(1, 3)], (
    app.session.recorder.default_moves
)
assert app.session.game.towers == [[3, 2], [], [1]], app.session.game.towers

# Disc 2 onto disc 1 is illegal: it comes back down its own peg.
drag(app, size=2, from_peg=0, to_peg=2)
assert app.session.recorder.default_moves == [(1, 3)]
assert app.session.game.towers == [[3, 2], [], [1]]
assert "larger on smaller" in app.message, app.message

# Both drawing paths run (the lit scene, and the ID buffer on screen).
app.draw()
app.show_pick_buffer = True
app.draw()
assert GL.glGetError() == GL.GL_NO_ERROR
glfw.terminate()
print("GL SMOKE OK")
