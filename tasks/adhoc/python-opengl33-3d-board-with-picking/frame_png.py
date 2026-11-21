"""Save the 3D board's lit frame and its pick (ID) buffer as PNG files.

One-shot visual check for hanoi-gl: renders a game a few moves in, reads the
back buffer with glReadPixels (llvmpipe windows capture black in a
screenshot), and writes `lit.png` and `pick.png` (IDs brightened so they are
visible) to the directory given as the first argument. Run from python/ under
Xvfb, like tools/gl_smoke.py.
"""

import pathlib
import struct
import sys
import zlib

import glfw
import numpy as np
import OpenGL.GL as GL
from numpy.typing import NDArray

from hanoigame.commands import MoveCmd
from hanoigame.hanoigl import HanoiGL


def write_png(path: pathlib.Path, rgb: NDArray[np.uint8]) -> None:
    """Write an (H, W, 3) uint8 image as a PNG (top row first)."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        """One length-prefixed, CRC-suffixed PNG chunk."""
        body: bytes = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(
            ">I", zlib.crc32(body)
        )

    height: int
    width: int
    height, width = rgb.shape[:2]
    rows: bytes = b"".join(b"\x00" + bytes(row) for row in rgb)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def grab(width: int, height: int) -> NDArray[np.uint8]:
    """Read the back buffer as an (H, W, 3) image, top row first."""
    GL.glReadBuffer(GL.GL_BACK)
    GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1)
    raw: bytes = bytes(
        GL.glReadPixels(0, 0, width, height, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
    )
    return np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 3)[::-1]


out: pathlib.Path = pathlib.Path(sys.argv[1])
assert glfw.init()
glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL.GL_TRUE)
window: object = glfw.create_window(900, 600, "frame", None, None)
glfw.make_context_current(window)
app: HanoiGL = HanoiGL(window, num_disks=4)
move: MoveCmd
for move in (MoveCmd(1, 2), MoveCmd(1, 3), MoveCmd(2, 3)):
    app.session.dispatch(move)
app.camera.yaw = 0.4
width: int
height: int
width, height = glfw.get_framebuffer_size(window)
app.draw()
write_png(out / "lit.png", grab(width, height))
app.show_pick_buffer = True
app.draw()
ids: NDArray[np.uint8] = grab(width, height)
write_png(out / "pick.png", np.minimum(ids.astype(np.int32) * 60, 255).astype(np.uint8))
glfw.terminate()
print("wrote", out / "lit.png", out / "pick.png")
