"""Headless smoke for the OpenGL 3D front-end (hanoi-gl): imgui UI + picking.

A manual, display-dependent check that the format/type-check/test gates can't
reach -- NOT wired into any gate (it needs an X display with OpenGL 3.3; Mesa's
llvmpipe in Xvfb is enough). Run it from the Python subproject:

    cd python
    podman run --rm --entrypoint /bin/bash \
      -v "$PWD":/hanoi-python:Z hanoi-python \
      -c 'dnf install -y xorg-x11-server-Xvfb >/dev/null 2>&1; \
          cd /hanoi-python && xvfb-run -a -s "-screen 0 1280x800x24" \
          python tools/gl_smoke.py [frame.ppm]'

Prints "GL SMOKE OK" on success. It runs imgui frames (menus, panel, dialogs);
checks that a left press on the background does not turn the camera and that a
right-button drag does (the board follows the hand, and an unusable cursor
position does not spin it); picks the top disc through the offscreen colour-ID
pass and drags it to peg 3;
tries an illegal drop; wins a 1-disc game, saves the recipe, relabels and
applies it (the three-panel view); and reviews the history, declining and
then accepting "Continue from here?". With an argument, it also writes the
last frame as a PPM image for checking by eye.
"""

import pathlib
import sys

import glfw
import OpenGL.GL as GL
from imgui_bundle import imgui
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer

from hanoigame.hanoigl import (
    DISC_THICKNESS,
    HOLE_RADIUS,
    HanoiGL,
    outer_radius,
    peg_x,
    rest_y,
)


def run_frames(app: HanoiGL, renderer: GlfwRenderer, count: int) -> None:
    """Draw `count` frames of 1/60 s each."""
    _frame: int
    for _frame in range(count):
        glfw.poll_events()
        renderer.process_inputs()
        app.frame(1 / 60)
        renderer.render(imgui.get_draw_data())


def drag(
    app: HanoiGL, renderer: GlfwRenderer, size: int, from_peg: int, to_peg: int
) -> None:
    """Pick disc `size` off `from_peg`, carry it over `to_peg`, drop it, and
    run frames until it lands (the mouse is simulated by calling the app's
    press/cursor/release handlers)."""
    n: int = app.session.num_disks
    index: int = len(app.shown_game().towers[from_peg]) - 1
    # The disc's centre is its hole (the peg), so aim at the top face, midway
    # between the hole and the edge on the right side.
    app.press(
        *app.screen_point(
            peg_x(from_peg) + (HOLE_RADIUS + outer_radius(size, n)) / 2.0,
            rest_y(index) + DISC_THICKNESS / 2.0,
            0.0,
        )
    )
    assert app.moving is not None, f"disc {size} not picked: {app.status}"
    assert app.moving.size == size, app.moving
    _frame: int
    for _frame in range(100):
        app.update(1 / 60)
    app.cursor(*app.screen_point(peg_x(to_peg), 3.0, 0.0))
    for _frame in range(100):
        app.update(1 / 60)
    app.release()
    for _frame in range(300):
        app.update(1 / 60)
    assert app.moving is None, app.moving


assert glfw.init(), "glfw.init failed"
glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
window: object = glfw.create_window(1280, 800, "gl smoke", None, None)
assert window, "no OpenGL 3.3 core window"
glfw.make_context_current(window)
GL.glBindVertexArray(GL.glGenVertexArrays(1))
print("GL_VERSION", GL.glGetString(GL.GL_VERSION).decode())
imgui.create_context()
renderer: GlfwRenderer = GlfwRenderer(window)
app: HanoiGL = HanoiGL(window, num_disks=3)
run_frames(app, renderer, 3)  # menus, panel, the first-run How to Play

# A point above the board hits only the background clear colour: ID 0.
assert app.pick_at(*app.screen_point(0.0, 9.0, 0.0)) == 0

# A left press on the background does not turn the camera; it says how to.
app.press(*app.screen_point(0.0, 9.0, 0.0))
assert not app.orbiting and "right or middle" in app.status, app.status
app.release()

# A right-button drag to the right turns the board's near side to the right,
# and a drag down tilts the near side down (the camera looks from higher).
near_before: tuple[float, float] = app.screen_point(0.0, 0.0, 2.0)
app.start_orbit()
app.orbit_to(600.0, 400.0, valid=True)
app.orbit_to(640.0, 420.0, valid=True)
# An unusable position (unfocused window: (-1, -1)) restarts the drag
# instead of turning by the jump to it.
yaw_before_jump: float = app.camera.target_yaw
app.orbit_to(-1.0, -1.0, valid=True)
app.orbit_to(640.0, 420.0, valid=True)
app.orbit_to(10.0, 10.0, valid=False)
assert app.camera.target_yaw == yaw_before_jump
app.end_orbit()
_step: int
for _step in range(60):
    app.camera.follow(1 / 60)
near_after: tuple[float, float] = app.screen_point(0.0, 0.0, 2.0)
assert near_after[0] > near_before[0], (near_before, near_after)
assert near_after[1] > near_before[1], (near_before, near_after)
app.camera.yaw = app.camera.target_yaw = 0.0
app.camera.pitch = app.camera.target_pitch = 0.35
run_frames(app, renderer, 2)

# Smallest disc 1 -> 3: lifted, carried, lowered, recorded by the engine.
drag(app, renderer, size=1, from_peg=0, to_peg=2)
assert app.session.recorder.default_moves == [(1, 3)], (
    app.session.recorder.default_moves
)
# Disc 2 onto disc 1 is illegal: it slides home and the reason pops up.
drag(app, renderer, size=2, from_peg=0, to_peg=2)
assert app.session.recorder.default_moves == [(1, 3)]
assert "larger on smaller" in app.illegal_message, app.illegal_message
run_frames(app, renderer, 2)

# The keyboard move ends in make_move, the same path as a drop.
app.make_move(1, 2)
assert app.session.recorder.default_moves == [(1, 3), (1, 2)]

# History review: the board after move 1; a move asks first. "No" keeps the
# game; "Yes" deletes the later move, then makes the held one.
app.review_move(1)
assert app.shown_game().towers == [[3, 2], [], [1]]
app.make_move(1, 2)
assert app.pending is not None and app.session.current_moves == 2
app.pending = None  # the "No" button
app.make_move(1, 2)
app.continue_from_review()  # the "Yes" button
assert app.review_count is None
assert app.session.recorder.default_moves == [(1, 3), (1, 2)]
run_frames(app, renderer, 2)

# A 1-disc win unlocks Tier 2; save it, relabel, and apply it (the rebinding
# view under a relabelling).
app.new_game(1)
app.make_move(1, 3)
assert app.won_once and app.session.is_won()
app.save_recipe("solve-1")
assert "solve-1" in app.registry.names()
app.new_game(2)
app.relabel((1, 3, 2))
app.apply_recipe("solve-1")
assert app.view is not None and app.view.title == "Rebinding for 'solve-1'"
assert app.session.game.towers == [[2], [1], []], app.session.game.towers
app.view.selected = 0
app.show_pick_buffer = True
run_frames(app, renderer, 2)
app.show_pick_buffer = False
run_frames(app, renderer, 2)
assert GL.glGetError() == GL.GL_NO_ERROR

if len(sys.argv) > 1:
    width: int
    height: int
    width, height = glfw.get_framebuffer_size(window)
    glfw.poll_events()
    renderer.process_inputs()
    app.frame(1 / 60)
    renderer.render(imgui.get_draw_data())
    GL.glReadBuffer(GL.GL_BACK)
    GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1)
    pixels: bytes = bytes(
        GL.glReadPixels(0, 0, width, height, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
    )
    rows: list[bytes] = [
        pixels[row * width * 3 : (row + 1) * width * 3]
        for row in reversed(range(height))
    ]
    pathlib.Path(sys.argv[1]).write_bytes(
        f"P6 {width} {height} 255\n".encode() + b"".join(rows)
    )
renderer.shutdown()
glfw.terminate()
print("GL SMOKE OK")
