"""hanoi-gl: the 3D Towers of Hanoi in OpenGL 3.3 core, with a Dear ImGui UI.

Every feature the other GUIs have (feature-spec §7): relabelling, recipes
with the three-panel rebinding view, the always-visible move history with
review, the move buttons, the valid moves, the learning-flow tiers, How to
Play and the win celebration. The interface is Dear ImGui through
imgui-bundle, the way github.com/billsix/modelviewprojection's demos use it;
the board is drawn in 3D underneath. Discs are tori and pegs cylinders,
generated in code, and an orbit camera turns around the board (drag the
background, or with the right button; the wheel zooms).

The board teaches **selection by colour ID**:

1. On mouse-down, the scene is drawn once more into an offscreen framebuffer
   object (FBO) that is never shown. Every pickable object (each disc) is drawn
   in one flat colour that *encodes its ID* (`id_to_rgb`); everything else
   (pegs, base) is drawn in ID 0, so it still hides the discs behind it.
2. `glReadPixels` reads the one pixel under the cursor and `rgb_bytes_to_id`
   decodes the colour back into the ID: the disc that was clicked.
3. The normal, lit frame is then drawn to the window as usual.

View -> Show pick buffer (or ``P``) shows the ID buffer instead.

A picked top disc slides **up its peg until its hole clears the peg top**,
follows the cursor above the pegs, and on release slides down onto the nearest
peg. Collision detection keeps it physical: a disc moves sideways only where it
would not intersect a peg (`collides_with_peg`), so it must clear the peg top
first, and it comes down until it rests on that peg's top disc (`rest_y`). An
illegal drop (larger on smaller) slides back down its own peg. A drop and a
move button take the same path (`HanoiGL.make_move`) through the shared engine
(`engine.GameSession.dispatch`), like every other front-end.

The transforms use the matrix stack of gacalc
(github.com/billsix/geometricalgebra), the same one modelviewprojection's demos
use, so the picking code can be lifted into that book.
"""

import ctypes
import dataclasses
import enum
import math
import sys
import typing
from collections.abc import Sequence

import gacalc.gl.matrix_stack as ms

# Import glfw before imgui_bundle, so the standard glfw is the one loaded (as
# github.com/billsix/modelviewprojection's demos do).
import glfw
import numpy as np
import OpenGL.GL as GL
import OpenGL.GL.shaders as shaders
from imgui_bundle import imgui
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer
from numpy.typing import NDArray

from .commands import ApplyCmd, MoveCmd, RelabelCmd
from .engine import DispatchResult, GameSession
from .hanoimodel import HanoiGame
from .presenter import (
    HOWTO_TEXT,
    Labelling,
    change_labels_on_pegs,
    default_recipe_name,
    format_move_tally,
    format_win_celebration,
)
from .recipe import Recipe, RecipeRegistry, rebinding, rebound_moves

if typing.TYPE_CHECKING:
    # glfw types window handles as `_GLFWwindowPointerT`: private, and absent
    # at runtime, so alias it for the annotations (as modelviewprojection does).
    from glfw import _GLFWwindowPointerT

    GLFWWindow: typing.TypeAlias = _GLFWwindowPointerT

# --- Board layout (world units; y is up, the pegs stand in the z = 0 plane) ---

PEG_SPACING: float = 3.0
PEG_RADIUS: float = 0.12
TUBE_RADIUS: float = 0.18  # a disc's thickness is twice this
BASE_TOP: float = 0.0
BASE_HEIGHT: float = 0.3
MAX_DISKS: int = 8  # the disc colours run out after 8
DEFAULT_DISKS: int = 3
SLIDE_SPEED: float = 6.0  # world units per second for every disc motion


def peg_x(peg: int) -> float:
    """The x coordinate of physical peg 0, 1 or 2.

    Examples:
        >>> [peg_x(peg) for peg in range(3)]
        [-3.0, 0.0, 3.0]
    """
    return (peg - 1) * PEG_SPACING


def nearest_peg(x: float) -> int:
    """The physical peg whose axis is closest to x (forgiving targeting).

    Examples:
        >>> nearest_peg(-2.0), nearest_peg(0.4), nearest_peg(9.0)
        (0, 1, 2)
    """
    return min(range(3), key=lambda peg: abs(x - peg_x(peg)))


def major_radius(size: int, num_disks: int) -> float:
    """A disc's torus radius (centre of the hole to the centre of the tube).

    The smallest disc's hole just fits around a peg; the largest disc's outer
    edge stays clear of the neighbouring disc stacks.

    Examples:
        >>> round(major_radius(1, 3), 2), round(major_radius(3, 3), 2)
        (0.35, 1.27)
    """
    smallest: float = PEG_RADIUS + TUBE_RADIUS + 0.05
    largest: float = PEG_SPACING / 2.0 - 0.05 - TUBE_RADIUS
    return smallest + (size - 1) * (largest - smallest) / max(num_disks - 1, 1)


def rest_y(stack_index: int) -> float:
    """The centre height of a disc resting at `stack_index` (0 = on the base).

    Examples:
        >>> round(rest_y(0), 2), round(rest_y(2), 2)
        (0.18, 0.9)
    """
    return BASE_TOP + TUBE_RADIUS + stack_index * 2.0 * TUBE_RADIUS


def peg_height(num_disks: int) -> float:
    """How far a peg stands above the base: the full stack plus a margin."""
    return num_disks * 2.0 * TUBE_RADIUS + 0.6


def carry_y(num_disks: int) -> float:
    """The centre height of a carried disc: its bottom just above the pegs.

    Examples:
        >>> carry_y(3) > BASE_TOP + peg_height(3) + TUBE_RADIUS
        True
    """
    return BASE_TOP + peg_height(num_disks) + TUBE_RADIUS + 0.15


def collides_with_peg(
    x: float, y: float, size: int, num_disks: int, peg: int
) -> bool:
    """Whether a disc centred at (x, y) would intersect a peg's cylinder.

    The disc is a torus lying flat. It misses the peg if it is entirely above
    the peg top, or if the peg passes wholly through its hole, or if the peg
    is wholly outside its outer edge.

    Args:
        x: The disc centre's x (the disc stays in the z = 0 plane).
        y: The disc centre's height.
        size: The disc size (sets its radius).
        num_disks: The game's disc count (sets the radii and the peg height).
        peg: The physical peg (0, 1, 2) to test against.

    Returns:
        True when the two solids overlap.

    Examples:
        A disc around its own peg, at rest, is fine; slid sideways it hits:

        >>> collides_with_peg(peg_x(0), rest_y(0), 1, 3, peg=0)
        False
        >>> collides_with_peg(peg_x(0) + 0.5, rest_y(0), 1, 3, peg=0)
        True
        >>> collides_with_peg(peg_x(0) + 0.5, carry_y(3), 1, 3, peg=0)
        False
    """
    peg_top: float = BASE_TOP + peg_height(num_disks)
    if y - TUBE_RADIUS >= peg_top:
        return False
    distance: float = abs(x - peg_x(peg))
    radius: float = major_radius(size, num_disks)
    inside_hole: bool = distance + PEG_RADIUS <= radius - TUBE_RADIUS
    outside_edge: bool = distance - PEG_RADIUS >= radius + TUBE_RADIUS
    return not (inside_hole or outside_edge)


def collides_with_any_peg(
    x: float, y: float, size: int, num_disks: int
) -> bool:
    """Whether a disc at (x, y) would intersect any of the three pegs."""
    return any(
        collides_with_peg(x, y, size, num_disks, peg) for peg in range(3)
    )


# --- Colour-ID picking: an object ID <-> the colour it is drawn in ---------


def id_to_rgb(object_id: int) -> tuple[float, float, float]:
    """The flat colour that object `object_id` is drawn in for picking.

    The ID's low, middle and high bytes become the red, green and blue
    channels (as 0-1 floats for the shader), so up to 2**24 - 1 objects can
    be told apart; ID 0 is black, "nothing".

    Examples:
        >>> id_to_rgb(0)
        (0.0, 0.0, 0.0)
        >>> id_to_rgb(1)[0] == 1 / 255
        True
    """
    return (
        (object_id & 0xFF) / 255.0,
        ((object_id >> 8) & 0xFF) / 255.0,
        ((object_id >> 16) & 0xFF) / 255.0,
    )


def rgb_bytes_to_id(red: int, green: int, blue: int) -> int:
    """Decode a pixel read back from the pick buffer into an object ID.

    Examples:
        >>> rgb_bytes_to_id(3, 0, 0)
        3
        >>> all(
        ...     rgb_bytes_to_id(*(round(c * 255) for c in id_to_rgb(i))) == i
        ...     for i in (0, 1, 7, 300, 70000)
        ... )
        True
    """
    return red | (green << 8) | (blue << 16)


# --- Meshes: generated geometry, interleaved position + normal --------------


def torus_mesh(
    radius: float, tube: float, rings: int = 48, sides: int = 16
) -> tuple[NDArray[np.float32], NDArray[np.uint32]]:
    """A torus lying flat (its axis is y), as vertices and triangle indices.

    A point on it is (R + r cos v) (cos u, 0, sin u) + r sin v (0, 1, 0), for
    u around the ring and v around the tube; the normal is that point minus
    the tube's centre line, (cos v cos u, sin v, cos v sin u).

    Args:
        radius: R, centre of the hole to the centre of the tube.
        tube: r, the radius of the tube.
        rings: Steps of u around the ring.
        sides: Steps of v around the tube.

    Returns:
        ``(vertices, indices)``: an (N, 6) float32 array of x, y, z, nx, ny, nz
        rows, and the uint32 indices of the triangles.

    Examples:
        >>> vertices, indices = torus_mesh(1.0, 0.25, rings=8, sides=4)
        >>> vertices.shape, indices.shape
        ((45, 6), (192,))
    """
    u: NDArray[np.float64] = np.linspace(0.0, 2.0 * math.pi, rings + 1)
    v: NDArray[np.float64] = np.linspace(0.0, 2.0 * math.pi, sides + 1)
    uu: NDArray[np.float64]
    vv: NDArray[np.float64]
    uu, vv = np.meshgrid(u, v, indexing="ij")
    normals: NDArray[np.float64] = np.stack(
        [np.cos(vv) * np.cos(uu), np.sin(vv), np.cos(vv) * np.sin(uu)], axis=-1
    )
    centre_line: NDArray[np.float64] = np.stack(
        [radius * np.cos(uu), np.zeros_like(uu), radius * np.sin(uu)], axis=-1
    )
    positions: NDArray[np.float64] = centre_line + tube * normals
    vertices: NDArray[np.float32] = (
        np.concatenate([positions, normals], axis=-1)
        .reshape(-1, 6)
        .astype(np.float32)
    )
    return vertices, _grid_indices(rings, sides)


def _grid_indices(rows: int, columns: int) -> NDArray[np.uint32]:
    """Two triangles per cell of a (rows + 1) x (columns + 1) vertex grid."""
    row: NDArray[np.uint32] = np.arange(rows, dtype=np.uint32)[:, None]
    column: NDArray[np.uint32] = np.arange(columns, dtype=np.uint32)[None, :]
    corner: NDArray[np.uint32] = row * (columns + 1) + column
    right: NDArray[np.uint32] = corner + columns + 1
    return (
        np.stack(
            [corner, right, corner + 1, corner + 1, right, right + 1], axis=-1
        )
        .reshape(-1)
        .astype(np.uint32)
    )


def cylinder_mesh(
    radius: float, height: float, sides: int = 24
) -> tuple[NDArray[np.float32], NDArray[np.uint32]]:
    """An upright cylinder (base at y = 0) with a flat top cap.

    Examples:
        >>> vertices, indices = cylinder_mesh(0.1, 2.0, sides=6)
        >>> vertices.shape, indices.shape
        ((22, 6), (54,))
    """
    angles: NDArray[np.float64] = np.linspace(0.0, 2.0 * math.pi, sides + 1)
    ring: NDArray[np.float64] = np.stack(
        [np.cos(angles), np.zeros_like(angles), np.sin(angles)], axis=-1
    )
    bottom: NDArray[np.float64] = np.concatenate([radius * ring, ring], axis=-1)
    top: NDArray[np.float64] = bottom + np.array([0, height, 0, 0, 0, 0])
    side: NDArray[np.uint32] = _grid_indices(1, sides)
    up: NDArray[np.float64] = np.array([0.0, 1.0, 0.0])
    cap_ring: NDArray[np.float64] = np.concatenate(
        [radius * ring + height * up, np.tile(up, (sides + 1, 1))], axis=-1
    )
    cap_centre: NDArray[np.float64] = np.array([[0.0, height, 0.0, *up]])
    first_cap: int = 2 * (sides + 1)
    centre_index: int = first_cap + sides + 1
    cap: NDArray[np.uint32] = np.array(
        [
            [centre_index, first_cap + i + 1, first_cap + i]
            for i in range(sides)
        ],
        dtype=np.uint32,
    ).reshape(-1)
    vertices: NDArray[np.float32] = np.concatenate(
        [bottom, top, cap_ring, cap_centre]
    ).astype(np.float32)
    return vertices, np.concatenate([side, cap]).astype(np.uint32)


def box_mesh(
    width: float, height: float, depth: float
) -> tuple[NDArray[np.float32], NDArray[np.uint32]]:
    """A box centred on x and z, standing on y = 0, with flat-shaded faces.

    Examples:
        >>> vertices, indices = box_mesh(1.0, 1.0, 1.0)
        >>> vertices.shape, indices.shape
        ((24, 6), (36,))
    """
    half: NDArray[np.float64] = np.array([width / 2.0, height, depth / 2.0])
    faces: list[list[float]] = []
    axis: int
    for axis in range(3):
        sign: float
        for sign in (-1.0, 1.0):
            normal: NDArray[np.float64] = np.zeros(3)
            normal[axis] = sign
            others: list[int] = [i for i in range(3) if i != axis]
            corner_a: float
            corner_b: float
            for corner_a, corner_b in ((0, 0), (1, 0), (1, 1), (0, 1)):
                point: NDArray[np.float64] = np.zeros(3)
                point[axis] = sign
                point[others[0]] = corner_a * 2 - 1
                point[others[1]] = corner_b * 2 - 1
                # Map -1..1 onto the box; y runs 0..height, not centred.
                position: NDArray[np.float64] = point * half
                position[1] = (point[1] + 1.0) / 2.0 * height
                faces.append([*position, *normal])
    face_indices: list[int] = []
    face: int
    for face in range(6):
        base: int = 4 * face
        face_indices.extend(
            [base, base + 1, base + 2, base, base + 2, base + 3]
        )
    return (
        np.array(faces, dtype=np.float32),
        np.array(face_indices, dtype=np.uint32),
    )


# --- The disc being moved: lift, carry, lower, with collision checks --------


class Phase(enum.Enum):
    """Where a moving disc is in its trip from one peg to another."""

    LIFTING = enum.auto()  # rising along its own peg until it clears the top
    CARRYING = enum.auto()  # above the pegs, following the cursor
    LOWERING = enum.auto()  # over the target peg, then down onto its stack


@dataclasses.dataclass
class MovingDisc:
    """A disc taken off a peg: where it is and where it is going.

    Attributes:
        size: The disc's size.
        source: The physical peg it was lifted from.
        x: The disc centre's x now.
        y: The disc centre's height now.
        phase: Which part of the trip it is in.
        released: Whether the mouse button is up (the drop target is chosen).
        target: The peg it will come down on, once released.
        target_y: The height it comes to rest at on `target`.
    """

    size: int
    source: int
    x: float
    y: float
    phase: Phase = Phase.LIFTING
    released: bool = False
    target: int = 0
    target_y: float = 0.0

    def advance(self, dt: float, cursor_x: float, num_disks: int) -> bool:
        """Move the disc for `dt` seconds; return True once it has landed.

        Sideways motion is refused wherever it would intersect a peg, so a
        disc can only leave its peg by rising above the peg top first.

        Args:
            dt: Seconds since the last frame.
            cursor_x: Where the cursor is over the board (used while carrying).
            num_disks: The game's disc count (radii, peg height).

        Returns:
            True when the disc has come to rest on `target`.

        Examples:
            A disc lifted off peg 0 and dropped on peg 2 rises, crosses and
            comes down onto the empty peg:

            >>> disc = MovingDisc(size=1, source=0, x=peg_x(0), y=rest_y(2))
            >>> disc.released, disc.target, disc.target_y = True, 2, rest_y(0)
            >>> landed = False
            >>> while not landed:
            ...     landed = disc.advance(0.01, cursor_x=0.0, num_disks=3)
            >>> (disc.x, disc.y) == (peg_x(2), rest_y(0))
            True
        """
        step: float = SLIDE_SPEED * dt
        top: float = carry_y(num_disks)
        match self.phase:
            case Phase.LIFTING:
                self.y = min(self.y + step, top)
                if self.y >= top:
                    self.phase = (
                        Phase.LOWERING if self.released else Phase.CARRYING
                    )
            case Phase.CARRYING:
                self._slide_towards(cursor_x, step, num_disks)
                if self.released:
                    self.phase = Phase.LOWERING
            case Phase.LOWERING:
                goal_x: float = peg_x(self.target)
                if self.x != goal_x:
                    self._slide_towards(goal_x, step, num_disks)
                else:
                    self.y = max(self.y - step, self.target_y)
                    return self.y <= self.target_y
            case _:
                raise ValueError(f"unknown phase {self.phase}")
        return False

    def _slide_towards(
        self, goal_x: float, step: float, num_disks: int
    ) -> None:
        """Move x toward goal_x by at most `step`, unless that would collide."""
        clamped: float = min(max(goal_x, peg_x(0)), peg_x(2))
        new_x: float = self.x + max(-step, min(step, clamped - self.x))
        if not collides_with_any_peg(new_x, self.y, self.size, num_disks):
            self.x = new_x


# --- GPU side: shaders, meshes, the pick framebuffer ------------------------

LIT_VERTEX_SHADER: str = """
#version 330 core
layout(location = 0) in vec3 position;
layout(location = 1) in vec3 normal;
uniform mat4 mvp;
uniform mat4 modelview;
uniform mat3 normal_matrix;
out vec3 view_normal;
out vec3 view_position;
void main() {
    view_normal = normal_matrix * normal;
    view_position = (modelview * vec4(position, 1.0)).xyz;
    gl_Position = mvp * vec4(position, 1.0);
}
"""

LIT_FRAGMENT_SHADER: str = """
#version 330 core
in vec3 view_normal;
in vec3 view_position;
uniform vec3 color;
out vec4 frag_color;
void main() {
    vec3 n = normalize(view_normal);
    vec3 light = normalize(vec3(0.4, 0.8, 0.6));
    vec3 to_eye = normalize(-view_position);
    float diffuse = max(dot(n, light), 0.0);
    float specular = pow(max(dot(reflect(-light, n), to_eye), 0.0), 32.0);
    frag_color = vec4(color * (0.25 + 0.75 * diffuse) + 0.25 * specular, 1.0);
}
"""

# The pick pass: no lighting, no blending, just the object's ID as its colour.
PICK_VERTEX_SHADER: str = """
#version 330 core
layout(location = 0) in vec3 position;
uniform mat4 mvp;
void main() {
    gl_Position = mvp * vec4(position, 1.0);
}
"""

PICK_FRAGMENT_SHADER: str = """
#version 330 core
uniform vec3 id_color;
uniform float brightness;  // 1 for picking; larger only to show IDs on screen
out vec4 frag_color;
void main() {
    frag_color = vec4(min(id_color * brightness, vec3(1.0)), 1.0);
}
"""

# Disc colours by size (smallest first), as the wx board's palette.
DISC_COLOURS: list[tuple[float, float, float]] = [
    (0.91, 0.30, 0.24),
    (0.95, 0.55, 0.20),
    (0.95, 0.77, 0.25),
    (0.40, 0.75, 0.35),
    (0.25, 0.60, 0.85),
    (0.45, 0.40, 0.80),
    (0.75, 0.40, 0.70),
    (0.60, 0.60, 0.60),
]
WOOD: tuple[float, float, float] = (0.62, 0.45, 0.28)


class Mesh:
    """Geometry uploaded to the GPU: one VAO with position and normal."""

    def __init__(
        self, vertices: NDArray[np.float32], indices: NDArray[np.uint32]
    ) -> None:
        """Upload interleaved x, y, z, nx, ny, nz vertices and indices."""
        self.count: int = int(indices.size)
        self.vao: int = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        self.vbo: int = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
        GL.glBufferData(
            GL.GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL.GL_STATIC_DRAW
        )
        self.ebo: int = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        GL.glBufferData(
            GL.GL_ELEMENT_ARRAY_BUFFER,
            indices.nbytes,
            indices,
            GL.GL_STATIC_DRAW,
        )
        stride: int = 6 * 4
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(
            0, 3, GL.GL_FLOAT, GL.GL_FALSE, stride, ctypes.c_void_p(0)
        )
        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(
            1, 3, GL.GL_FLOAT, GL.GL_FALSE, stride, ctypes.c_void_p(12)
        )

    def draw(self) -> None:
        """Draw the triangles (a program must be in use)."""
        GL.glBindVertexArray(self.vao)
        GL.glDrawElements(
            GL.GL_TRIANGLES, self.count, GL.GL_UNSIGNED_INT, ctypes.c_void_p(0)
        )


class PickBuffer:
    """The offscreen framebuffer the pick pass draws into; never shown."""

    def __init__(self, width: int, height: int) -> None:
        """Create the framebuffer with a colour and a depth attachment."""
        self.fbo: int = GL.glGenFramebuffers(1)
        self.color: int = GL.glGenRenderbuffers(1)
        self.depth: int = GL.glGenRenderbuffers(1)
        self.width: int = 0
        self.height: int = 0
        self.resize(width, height)

    def resize(self, width: int, height: int) -> None:
        """Match the window's framebuffer size (one pick pixel per pixel)."""
        self.width, self.height = max(width, 1), max(height, 1)
        GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, self.color)
        GL.glRenderbufferStorage(
            GL.GL_RENDERBUFFER, GL.GL_RGBA8, self.width, self.height
        )
        GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, self.depth)
        GL.glRenderbufferStorage(
            GL.GL_RENDERBUFFER, GL.GL_DEPTH_COMPONENT24, self.width, self.height
        )
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.fbo)
        GL.glFramebufferRenderbuffer(
            GL.GL_FRAMEBUFFER,
            GL.GL_COLOR_ATTACHMENT0,
            GL.GL_RENDERBUFFER,
            self.color,
        )
        GL.glFramebufferRenderbuffer(
            GL.GL_FRAMEBUFFER,
            GL.GL_DEPTH_ATTACHMENT,
            GL.GL_RENDERBUFFER,
            self.depth,
        )
        status: int = GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        if status != GL.GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError(f"pick framebuffer incomplete: {status:#x}")


# --- The camera ------------------------------------------------------------


@dataclasses.dataclass
class OrbitCamera:
    """A camera on a sphere around the board's centre.

    Attributes:
        yaw: Turn around the vertical axis, in radians.
        pitch: Tilt down toward the board, in radians.
        distance: Distance from the point it looks at.
    """

    yaw: float = 0.0
    pitch: float = 0.35
    distance: float = 11.0

    def orbit(self, dx: float, dy: float) -> None:
        """Turn by a mouse drag of (dx, dy) pixels; the pitch stays above the
        board and short of straight down."""
        self.yaw += dx * 0.01
        self.pitch = min(max(self.pitch + dy * 0.01, 0.05), 1.45)

    def zoom(self, steps: float) -> None:
        """Move closer (positive steps) or further away, within limits."""
        self.distance = min(max(self.distance * 0.9**steps, 4.0), 30.0)


# --- The application -------------------------------------------------------

# Peg colours by LABEL (0-indexed), so a colour follows a label across
# relabels (feature-spec §4.3): blue, gold, red, as in the other GUIs.
LABEL_COLOURS: list[tuple[float, float, float]] = [
    (0.29, 0.47, 0.84),
    (0.86, 0.72, 0.24),
    (0.84, 0.33, 0.33),
]
PANEL_WIDTH: float = 380.0  # the right-hand Game panel, in imgui units
MOVE_PAIRS: tuple[tuple[int, int], ...] = (
    (1, 2),
    (1, 3),
    (2, 1),
    (2, 3),
    (3, 1),
    (3, 2),
)
RELABEL_PERMUTATIONS: tuple[tuple[int, int, int], ...] = (
    (1, 2, 3),
    (1, 3, 2),
    (2, 1, 3),
    (2, 3, 1),
    (3, 1, 2),
    (3, 2, 1),
)


def ascii_text(text: str) -> str:
    """The text with the few non-ASCII marks the shared lines use replaced.

    ImGui's built-in font covers ASCII only; a dash or an arrow would show
    as "?".

    Examples:
        >>> ascii_text("1 → 3 — done • ok")
        '1 -> 3 -- done - ok'
    """
    return (
        text.replace("→", "->")
        .replace("—", "--")
        .replace("•", "-")
        .replace("‘", "'")
        .replace("’", "'")
    )


@dataclasses.dataclass
class RebindingView:
    """The three-panel rebinding view (feature-spec §4.8), or a recipe list.

    Attributes:
        title: The heading over the view.
        left_header: The left column's header (whose labels the moves use).
        moves: The moves in their own labels.
        labelling: The labelling active when the view was opened.
        selected: The selected move's row, or None.
    """

    title: str
    left_header: str
    moves: list[tuple[int, int]]
    labelling: Labelling
    selected: int | None = None


@dataclasses.dataclass
class PendingAction:
    """A move (by labels) or a recipe apply, asked for while reviewing the
    history and held until the student answers "Continue from here?"."""

    move: tuple[int, int] | None = None
    apply_name: str | None = None


class HanoiGL:
    """The 3D board with a Dear ImGui interface: every feature of the other
    GUIs (feature-spec §7), with the board drawn in 3D and picked by colour.

    `frame` draws one frame (UI, input, the 3D scene). The game actions
    (`make_move`, `relabel`, `apply_recipe`, ...) are plain methods, so a
    test can drive them without the mouse.
    """

    def __init__(
        self, window: "GLFWWindow", num_disks: int = DEFAULT_DISKS
    ) -> None:
        """Build the GL resources for `window` (its context must be current,
        and an imgui context must exist).

        Args:
            window: The GLFW window.
            num_disks: Discs in the first game.
        """
        self.window: GLFWWindow = window
        self.registry: RecipeRegistry = RecipeRegistry()
        self.session: GameSession = GameSession(num_disks, self.registry)
        self.camera: OrbitCamera = OrbitCamera()
        self.moving: MovingDisc | None = None
        self.orbiting: bool = False
        self.last_cursor: tuple[float, float] = (0.0, 0.0)
        self.cursor_x: float = 0.0
        self.show_pick_buffer: bool = False
        self.want_quit: bool = False
        self.status: str = ""
        # Tier-2 gating (feature-spec §3.5): relabel + recipes unlock at the
        # first win and stay unlocked for the session.
        self.won_once: bool = False
        # Win celebration and save-before-discard (§4.9): the shared lines,
        # whether the win came from replaying a recipe or was already saved,
        # and a New Game held behind the save question.
        self.win_lines: list[str] = []
        self.won_via_apply: bool = False
        self.saved_current: bool = False
        self.pending_new_game: int | None = None
        self.view: RebindingView | None = None
        # History review (§4.11): how many moves the board shows (None = the
        # live game), and a move or apply waiting on "Continue from here?".
        self.review_count: int | None = None
        self.pending: PendingAction | None = None
        self.illegal_message: str = ""
        self.recipe_name: str = ""
        # Popups to open on the next frame (imgui opens them by name).
        self.popups_to_open: list[str] = ["How to Play"]
        self.lit: int = shaders.compileProgram(
            shaders.compileShader(LIT_VERTEX_SHADER, GL.GL_VERTEX_SHADER),
            shaders.compileShader(LIT_FRAGMENT_SHADER, GL.GL_FRAGMENT_SHADER),
            validate=False,
        )
        self.pick: int = shaders.compileProgram(
            shaders.compileShader(PICK_VERTEX_SHADER, GL.GL_VERTEX_SHADER),
            shaders.compileShader(PICK_FRAGMENT_SHADER, GL.GL_FRAGMENT_SHADER),
            validate=False,
        )
        self.pick_buffer: PickBuffer = PickBuffer(1, 1)
        self.disc_meshes: dict[int, Mesh] = {}
        self.peg_mesh: Mesh
        self.base_mesh: Mesh
        self._build_meshes()

    # --- Game state ------------------------------------------------------

    def shown_game(self) -> HanoiGame:
        """The game the board shows: the reviewed state, or the live game."""
        if self.review_count is None:
            return self.session.game
        return self.session.state_after(self.review_count)

    def _label(self, peg: int) -> int:
        """The 1-indexed label physical peg `peg` wears now."""
        return change_labels_on_pegs(self.session.labelling, peg) + 1

    def legal_label_moves(self) -> set[tuple[int, int]]:
        """The legal moves on the board shown, as (from, to) labels."""
        return {
            (self._label(valid.move.from_peg), self._label(valid.move.to_peg))
            for valid in self.shown_game().move_options()
        }

    def request_new_game(self, num_disks: int) -> None:
        """New Game: if a hand-won solution was not saved, ask first."""
        if (
            self.session.is_won()
            and not self.won_via_apply
            and not self.saved_current
        ):
            self.pending_new_game = num_disks
            self.popups_to_open.append("Save solution?")
        else:
            self.new_game(num_disks)

    def new_game(self, num_disks: int) -> None:
        """Start a fresh game with `num_disks` discs; rebuild the meshes."""
        self.session = GameSession(num_disks, self.registry)
        self.moving = None
        self.status = ""
        self.view = None
        self.win_lines = []
        self.won_via_apply = False
        self.saved_current = False
        self.pending_new_game = None
        self.review_count = None
        self.pending = None
        self._build_meshes()

    def _build_meshes(self) -> None:
        """Generate the tori for this disc count, the pegs and the base."""
        n: int = self.session.num_disks
        self.disc_meshes = {
            size: Mesh(*torus_mesh(major_radius(size, n), TUBE_RADIUS))
            for size in range(1, n + 1)
        }
        self.peg_mesh = Mesh(*cylinder_mesh(PEG_RADIUS, peg_height(n)))
        self.base_mesh = Mesh(
            *box_mesh(3.0 * PEG_SPACING, BASE_HEIGHT, PEG_SPACING)
        )

    def make_move(self, from_label: int, to_label: int) -> None:
        """Make a move in the current labels: the one path for the move
        buttons and a dropped disc (feature-spec §4.2, ruling 7)."""
        if self.review_count is not None:
            self.pending = PendingAction(move=(from_label, to_label))
            self.popups_to_open.append("Continue from here?")
            return
        relabelled: bool = self.session.labelling != Labelling.ONE_TWO_THREE
        result: DispatchResult = self.session.dispatch(
            MoveCmd(from_label, to_label)
        )
        if result.lines:
            self.illegal_message = result.lines[0]
            self.status = result.lines[0]
            self.popups_to_open.append("Illegal move")
            return
        self.status = f"Moved {from_label} -> {to_label}."
        if relabelled:
            self.view = RebindingView(
                title="Rebinding for your move",
                left_header="Your move",
                moves=[(from_label, to_label)],
                labelling=self.session.labelling,
            )
        self._check_win()

    def relabel(self, labels: tuple[int, int, int]) -> None:
        """Relabel the pegs so physical pegs 1, 2, 3 show `labels`."""
        result: DispatchResult = self.session.dispatch(RelabelCmd(labels))
        self.status = result.lines[0] if result.lines else ""

    def save_recipe(self, name: str) -> None:
        """Save the won game's moves as recipe `name` (overwrite reported)."""
        self.status = self.session.save_recipe(name)
        self.saved_current = True

    def view_recipe(self, name: str) -> None:
        """Recipe menu -> View: the recipe's moves, and under a relabelling
        the three-panel rebinding view."""
        recipe: Recipe | None = self.registry.get(name)
        if recipe is None:
            return
        self.view = RebindingView(
            title=f"Recipe '{name}'",
            left_header="Recipe moves",
            moves=list(recipe.default_moves),
            labelling=self.session.labelling,
        )

    def apply_recipe(self, name: str) -> None:
        """Recipe menu -> Apply: replay the recipe through the current
        labelling; under a relabelling, show the rebinding view (§4.8)."""
        if self.review_count is not None:
            self.pending = PendingAction(apply_name=name)
            self.popups_to_open.append("Continue from here?")
            return
        recipe: Recipe | None = self.registry.get(name)
        if recipe is None:
            return
        relabelled: bool = self.session.labelling != Labelling.ONE_TWO_THREE
        result: DispatchResult = self.session.dispatch(ApplyCmd(name))
        stopped: list[str] = [
            line for line in result.lines if "stopped" in line.lower()
        ]
        self.status = (
            ascii_text(stopped[0])
            if stopped
            else f"Applied '{name}' -- {len(recipe.default_moves)} moves."
        )
        if relabelled:
            self.view = RebindingView(
                title=f"Rebinding for '{name}'",
                left_header="Recipe moves",
                moves=list(recipe.default_moves),
                labelling=self.session.labelling,
            )
        if self.session.is_won():
            self.won_via_apply = True
        self._check_win()

    def _check_win(self) -> None:
        """On a win: unlock Tier 2, put the result in the status line, and
        on the first win of the session show the recipe teaching (§4.9)."""
        if not self.session.is_won():
            return
        first_win: bool = not self.won_once
        self.won_once = True
        self.win_lines = [
            ascii_text(line)
            for line in format_win_celebration(
                self.session.num_disks,
                self.session.current_moves,
                self.session.min_moves(),
                first_win=first_win,
            )
        ]
        if self.win_lines:
            self.status = self.win_lines[0]
        if first_win:
            self.popups_to_open.append("You solved it!")

    def review_move(self, count: int) -> None:
        """Show the board after the first `count` moves; the last move is
        the live game, so it leaves review."""
        total: int = len(self.session.recorder.default_moves)
        self.review_count = count if count < total else None
        self.status = (
            f"Reviewing move {count} of {total}. Make a move to continue from"
            " here, or Back to current."
            if self.review_count is not None
            else ""
        )

    def continue_from_review(self) -> None:
        """Continue from the reviewed move: delete every later move, then
        make the held move or apply."""
        pending: PendingAction | None = self.pending
        self.pending = None
        if self.review_count is None:
            return
        self.session.truncate_to(self.review_count)
        self.review_count = None
        # The game changed, so a saved or replayed win no longer describes it.
        self.saved_current = False
        self.won_via_apply = False
        if pending is None:
            return
        if pending.move is not None:
            self.make_move(*pending.move)
        elif pending.apply_name is not None:
            self.apply_recipe(pending.apply_name)
        else:
            pass  # nothing was held

    # --- The board's rectangle and matrices ------------------------------

    def _board_rect(self) -> tuple[int, int, float, float]:
        """The board's size in framebuffer pixels, the imgui-to-pixel scale,
        and the menu bar's height in imgui units (the board starts there)."""
        width: int
        height: int
        width, height = glfw.get_framebuffer_size(self.window)
        io: imgui.IO = imgui.get_io()
        scale: float = width / max(io.display_size.x, 1.0)
        top: float = imgui.get_frame_height()
        board_width: int = max(int(width - PANEL_WIDTH * scale), 1)
        board_height: int = max(int(height - top * scale), 1)
        return board_width, board_height, scale, top

    def _set_view_projection(self) -> None:
        """Load the projection (for the board's aspect) and the orbit
        camera's view matrix."""
        board_width: int
        board_height: int
        board_width, board_height, _scale, _top = self._board_rect()
        ms.set_to_identity_matrix(ms.MatrixStack.projection)
        ms.perspective(45.0, board_width / board_height, 0.1, 100.0)
        ms.set_to_identity_matrix(ms.MatrixStack.view)
        # Read bottom-up: centre the board, turn it, tilt it, back away.
        ms.translate(ms.MatrixStack.view, 0.0, 0.0, -self.camera.distance)
        ms.rotate_x(ms.MatrixStack.view, self.camera.pitch)
        ms.rotate_y(ms.MatrixStack.view, -self.camera.yaw)
        ms.translate(ms.MatrixStack.view, 0.0, -1.2, 0.0)
        ms.set_to_identity_matrix(ms.MatrixStack.model)

    def _board_pixel(self, x: float, y: float) -> tuple[float, float]:
        """Window (imgui) point -> pixel in the board, counted from its
        top-left corner."""
        scale: float
        top: float
        _w, _h, scale, top = self._board_rect()
        return x * scale, (y - top) * scale

    def screen_point(self, x: float, y: float, z: float) -> tuple[float, float]:
        """Project world point (x, y, z) to window (imgui) coordinates."""
        board_width: int
        board_height: int
        scale: float
        top: float
        board_width, board_height, scale, top = self._board_rect()
        self._set_view_projection()
        clip: NDArray[np.float32] = ms.get_current_matrix(
            ms.MatrixStack.modelviewprojection
        ) @ np.array([x, y, z, 1.0])
        ndc_x: float = float(clip[0] / clip[3])
        ndc_y: float = float(clip[1] / clip[3])
        return (
            (ndc_x + 1.0) / 2.0 * board_width / scale,
            top + (1.0 - ndc_y) / 2.0 * board_height / scale,
        )

    def _scene(
        self,
    ) -> list[
        tuple[Mesh, tuple[float, float, float], tuple[float, float, float], int]
    ]:
        """Everything to draw: (mesh, position, colour, pick ID).

        Discs come from the board shown (the live game, or the reviewed
        state); the moving disc is drawn where it is now. Pegs and the base
        get pick ID 0, so they hide what is behind them but can't be picked.
        """
        items: list[
            tuple[
                Mesh,
                tuple[float, float, float],
                tuple[float, float, float],
                int,
            ]
        ] = [(self.base_mesh, (0.0, BASE_TOP - BASE_HEIGHT, 0.0), WOOD, 0)]
        peg: int
        for peg in range(3):
            items.append(
                (
                    self.peg_mesh,
                    (peg_x(peg), BASE_TOP, 0.0),
                    LABEL_COLOURS[self._label(peg) - 1],
                    0,
                )
            )
        stack: list[int]
        for peg, stack in enumerate(self.shown_game().towers):
            visible: list[int] = stack
            if self.moving is not None and self.moving.source == peg:
                visible = stack[:-1]
            index: int
            size: int
            for index, size in enumerate(visible):
                items.append(
                    (
                        self.disc_meshes[size],
                        (peg_x(peg), rest_y(index), 0.0),
                        DISC_COLOURS[size - 1],
                        size,
                    )
                )
        if self.moving is not None:
            items.append(
                (
                    self.disc_meshes[self.moving.size],
                    (self.moving.x, self.moving.y, 0.0),
                    DISC_COLOURS[self.moving.size - 1],
                    self.moving.size,
                )
            )
        return items

    # --- Drawing the 3D board --------------------------------------------

    def draw_board(self) -> None:
        """Draw the board into its rectangle: the lit scene, or the IDs."""
        board_width: int
        board_height: int
        board_width, board_height, _scale, _top = self._board_rect()
        GL.glViewport(0, 0, board_width, board_height)
        GL.glDisable(GL.GL_SCISSOR_TEST)  # imgui leaves it on
        GL.glClearColor(0.12, 0.14, 0.20, 1.0)
        # PyOpenGL's constants define no `|` for a type checker; at run time
        # they are ints.
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)  # ty: ignore[unsupported-operator]
        if self.show_pick_buffer:
            # IDs 1, 2, 3 are nearly black (1/255, 2/255, ...), so brighten
            # them for the eye; the real pick pass always uses brightness 1.
            self._draw_pick_pass(brightness=40.0)
            return
        GL.glDisable(GL.GL_BLEND)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glUseProgram(self.lit)
        self._set_view_projection()
        mesh: Mesh
        position: tuple[float, float, float]
        colour: tuple[float, float, float]
        for mesh, position, colour, _object_id in self._scene():
            with ms.push_matrix(ms.MatrixStack.model):
                ms.translate(ms.MatrixStack.model, *position)
                self._load_matrices(self.lit)
                GL.glUniform3f(
                    GL.glGetUniformLocation(self.lit, "color"), *colour
                )
                mesh.draw()

    def _draw_pick_pass(self, brightness: float = 1.0) -> None:
        """Draw every object in its ID colour into the bound framebuffer.

        Args:
            brightness: Multiplies the ID colours; 1 (exact IDs) for picking,
                larger only to make the IDs visible on screen.
        """
        GL.glDisable(GL.GL_BLEND)
        GL.glDisable(GL.GL_SCISSOR_TEST)
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)  # ty: ignore[unsupported-operator]
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glUseProgram(self.pick)
        GL.glUniform1f(
            GL.glGetUniformLocation(self.pick, "brightness"), brightness
        )
        self._set_view_projection()
        mesh: Mesh
        position: tuple[float, float, float]
        object_id: int
        for mesh, position, _colour, object_id in self._scene():
            with ms.push_matrix(ms.MatrixStack.model):
                ms.translate(ms.MatrixStack.model, *position)
                self._load_matrices(self.pick)
                GL.glUniform3f(
                    GL.glGetUniformLocation(self.pick, "id_color"),
                    *id_to_rgb(object_id),
                )
                mesh.draw()

    def _load_matrices(self, program: int) -> None:
        """Send the current model-view-projection (and, for the lit program,
        the model-view and normal matrices) to `program`'s uniforms."""
        mvp: NDArray[np.float32] = ms.get_current_matrix(
            ms.MatrixStack.modelviewprojection
        )
        GL.glUniformMatrix4fv(
            GL.glGetUniformLocation(program, "mvp"), 1, GL.GL_TRUE, mvp
        )
        if program != self.lit:
            return
        modelview: NDArray[np.float32] = ms.get_current_matrix(
            ms.MatrixStack.modelview
        )
        GL.glUniformMatrix4fv(
            GL.glGetUniformLocation(program, "modelview"),
            1,
            GL.GL_TRUE,
            modelview,
        )
        normal_matrix: NDArray[np.float32] = np.linalg.inv(
            modelview[:3, :3]
        ).T.astype(np.float32)
        GL.glUniformMatrix3fv(
            GL.glGetUniformLocation(program, "normal_matrix"),
            1,
            GL.GL_TRUE,
            normal_matrix,
        )

    def _draw_peg_labels(self) -> None:
        """Each peg's label under it (and, when relabelled, the physical
        "peg n" reference), drawn over the scene with imgui (§4.3)."""
        draw_list: imgui.ImDrawList = imgui.get_background_draw_list()
        relabelled: bool = self.session.labelling != Labelling.ONE_TWO_THREE
        peg: int
        for peg in range(3):
            x: float
            y: float
            x, y = self.screen_point(
                peg_x(peg), BASE_TOP - BASE_HEIGHT, PEG_SPACING / 2.0
            )
            red: float
            green: float
            blue: float
            red, green, blue = LABEL_COLOURS[self._label(peg) - 1]
            draw_list.add_text(
                imgui.ImVec2(x - 4.0, y + 4.0),
                imgui.get_color_u32(imgui.ImVec4(red, green, blue, 1.0)),
                str(self._label(peg)),
            )
            if relabelled:
                draw_list.add_text(
                    imgui.ImVec2(x - 22.0, y + 20.0),
                    imgui.get_color_u32(imgui.ImVec4(0.7, 0.7, 0.7, 1.0)),
                    f"(peg {peg + 1})",
                )

    # --- Picking and dragging --------------------------------------------

    def pick_at(self, x: float, y: float) -> int:
        """The ID of the object under window point (x, y), 0 for none.

        Renders the pick pass into the offscreen framebuffer, reads back the
        one pixel under the cursor, and decodes its colour. The window is not
        touched: the frame drawn next shows the normal scene.
        """
        board_width: int
        board_height: int
        board_width, board_height, _scale, _top = self._board_rect()
        if (board_width, board_height) != (
            self.pick_buffer.width,
            self.pick_buffer.height,
        ):
            self.pick_buffer.resize(board_width, board_height)
        pixel_x: float
        pixel_y: float
        pixel_x, pixel_y = self._board_pixel(x, y)
        if not (0 <= pixel_x < board_width and 0 <= pixel_y < board_height):
            return 0
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.pick_buffer.fbo)
        GL.glViewport(0, 0, board_width, board_height)
        self._draw_pick_pass()
        GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1)
        # GL's pixel rows count up from the bottom, so flip y.
        pixel: bytes = bytes(
            GL.glReadPixels(
                int(pixel_x),
                board_height - 1 - int(pixel_y),
                1,
                1,
                GL.GL_RGBA,
                GL.GL_UNSIGNED_BYTE,
            )
        )
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        return rgb_bytes_to_id(pixel[0], pixel[1], pixel[2])

    def board_x(self, x: float, y: float) -> float:
        """Where window point (x, y) falls on the z = 0 plane the pegs stand
        in, as a world x: the cursor ray through the inverse view-projection,
        intersected with that plane."""
        board_width: int
        board_height: int
        board_width, board_height, _scale, _top = self._board_rect()
        pixel_x: float
        pixel_y: float
        pixel_x, pixel_y = self._board_pixel(x, y)
        ndc_x: float = 2.0 * pixel_x / board_width - 1.0
        ndc_y: float = 1.0 - 2.0 * pixel_y / board_height
        self._set_view_projection()
        inverse: NDArray[np.float32] = np.linalg.inv(
            ms.get_current_matrix(ms.MatrixStack.modelviewprojection)
        )
        near: NDArray[np.float32] = inverse @ np.array(
            [ndc_x, ndc_y, -1.0, 1.0]
        )
        far: NDArray[np.float32] = inverse @ np.array([ndc_x, ndc_y, 1.0, 1.0])
        near_point: NDArray[np.float32] = near[:3] / near[3]
        far_point: NDArray[np.float32] = far[:3] / far[3]
        direction: NDArray[np.float32] = far_point - near_point
        if abs(direction[2]) < 1e-6:  # looking along the plane
            return self.cursor_x
        along: float = float(-near_point[2] / direction[2])
        return float(near_point[0] + along * direction[0])

    def press(self, x: float, y: float) -> None:
        """Mouse-down on the board at (x, y): pick up a top disc of the board
        shown, or start orbiting."""
        self.last_cursor = (x, y)
        if self.moving is not None:
            return
        picked: int = self.pick_at(x, y)
        board: HanoiGame = self.shown_game()
        tops: dict[int, int] = {
            stack[-1]: peg for peg, stack in enumerate(board.towers) if stack
        }
        if picked == 0:
            self.orbiting = True
        elif board.check_win_condition():
            self.status = "Solved! Start a new game from the Game menu."
        elif picked not in tops:
            self.status = f"Disc {picked} is not on top of its peg."
        else:
            source: int = tops[picked]
            self.moving = MovingDisc(
                size=picked,
                source=source,
                x=peg_x(source),
                y=rest_y(len(board.towers[source]) - 1),
            )
            self.cursor_x = self.moving.x

    def cursor(self, x: float, y: float) -> None:
        """Mouse moved to (x, y): orbit the camera, or steer a carried disc."""
        if self.orbiting:
            self.camera.orbit(x - self.last_cursor[0], y - self.last_cursor[1])
        elif self.moving is not None and not self.moving.released:
            self.cursor_x = self.board_x(x, y)
        self.last_cursor = (x, y)

    def release(self) -> None:
        """Mouse-up: stop orbiting, or drop the carried disc on the nearest
        peg if that move is legal; an illegal one slides back home and the
        reason pops up."""
        self.orbiting = False
        if self.moving is None or self.moving.released:
            return
        moving: MovingDisc = self.moving
        target: int = nearest_peg(moving.x)
        towers: list[list[int]] = self.shown_game().towers
        if (
            target != moving.source
            and towers[target]
            and (towers[target][-1] < moving.size)
        ):
            self.illegal_message = (
                f"Can't put disc {moving.size} on disc {towers[target][-1]}"
                " -- larger on smaller."
            )
            self.status = self.illegal_message
            self.popups_to_open.append("Illegal move")
            target = moving.source
        moving.released = True
        moving.target = target
        resting_on: int = len(towers[target]) - (target == moving.source)
        moving.target_y = rest_y(resting_on)

    def update(self, dt: float) -> None:
        """Advance the moving disc; when it lands on another peg, make the
        move through the same path as a move button."""
        if self.moving is None:
            return
        moving: MovingDisc = self.moving
        if not moving.advance(dt, self.cursor_x, self.session.num_disks):
            return
        self.moving = None
        if moving.target != moving.source:
            self.make_move(
                self._label(moving.source), self._label(moving.target)
            )

    def _board_input(self) -> None:
        """Mouse and keys on the board, unless imgui is using them (a menu,
        a window or a dialog is under the mouse or has the keyboard)."""
        io: imgui.IO = imgui.get_io()
        x: float = io.mouse_pos.x
        y: float = io.mouse_pos.y
        if not io.want_capture_mouse:
            if imgui.is_mouse_clicked(imgui.MouseButton_.left):
                self.press(x, y)
            if imgui.is_mouse_clicked(imgui.MouseButton_.right):
                self.orbiting = True
                self.last_cursor = (x, y)
            if io.mouse_wheel:
                self.camera.zoom(io.mouse_wheel)
        if (x, y) != self.last_cursor:
            self.cursor(x, y)
        if imgui.is_mouse_released(
            imgui.MouseButton_.left
        ) or imgui.is_mouse_released(imgui.MouseButton_.right):
            self.release()
        if not io.want_capture_keyboard:
            if imgui.is_key_pressed(imgui.Key.p):
                self.show_pick_buffer = not self.show_pick_buffer
            if imgui.is_key_pressed(imgui.Key.r):
                self.camera = OrbitCamera()

    # --- The imgui interface ---------------------------------------------

    def _menu_bar(self) -> None:
        """Game / Relabel / Recipe / View / Help (feature-spec §3.5, §6.2):
        Relabel and Recipe are dimmed until the first win."""
        if not imgui.begin_main_menu_bar():
            return
        if imgui.begin_menu("Game"):
            if imgui.begin_menu("New Game"):
                n: int
                for n in range(1, MAX_DISKS + 1):
                    if imgui.menu_item_simple(
                        f"{n} discs", selected=self.session.num_disks == n
                    ):
                        self.request_new_game(n)
                imgui.end_menu()
            if imgui.menu_item_simple("New Game (Same Size)"):
                self.request_new_game(self.session.num_disks)
            imgui.separator()
            if imgui.menu_item_simple("Quit"):
                self.want_quit = True
            imgui.end_menu()
        imgui.begin_disabled(not self.won_once)
        if imgui.begin_menu("Relabel"):
            current: tuple[int, ...] = tuple(self._label(p) for p in range(3))
            labels: tuple[int, int, int]
            for labels in RELABEL_PERMUTATIONS:
                if imgui.menu_item_simple(
                    "%d %d %d" % labels, selected=labels == current
                ):
                    self.relabel(labels)
            imgui.end_menu()
        if imgui.begin_menu("Recipe"):
            if imgui.menu_item_simple(
                "Save current solution", enabled=self.session.is_won()
            ):
                self.recipe_name = default_recipe_name(self.session.num_disks)
                self.popups_to_open.append("Save recipe")
            imgui.separator()
            names: list[str] = self.registry.names()
            if not names:
                imgui.menu_item_simple("(no saved recipes yet)", enabled=False)
            name: str
            for name in names:
                recipe: Recipe | None = self.registry.get(name)
                assert recipe is not None  # listed by the registry itself
                if imgui.begin_menu(
                    f"{name}  ({recipe.disk_count} discs,"
                    f" {len(recipe.default_moves)} moves)"
                ):
                    if imgui.menu_item_simple("View"):
                        self.view_recipe(name)
                    if imgui.menu_item_simple(
                        "Apply", enabled=not self.session.is_won()
                    ):
                        self.apply_recipe(name)
                    imgui.end_menu()
            imgui.end_menu()
        imgui.end_disabled()
        if imgui.begin_menu("View"):
            if imgui.menu_item_simple(
                "Show pick buffer", "P", selected=self.show_pick_buffer
            ):
                self.show_pick_buffer = not self.show_pick_buffer
            if imgui.menu_item_simple("Reset camera", "R"):
                self.camera = OrbitCamera()
            imgui.end_menu()
        if imgui.begin_menu("Help"):
            if imgui.menu_item_simple("How to Play"):
                self.popups_to_open.append("How to Play")
            imgui.end_menu()
        imgui.end_main_menu_bar()

    def _panel(self) -> None:
        """The right-hand Game panel: goal line, status, valid moves, move
        buttons, the move history with review, and the rebinding view."""
        io: imgui.IO = imgui.get_io()
        top: float = imgui.get_frame_height()
        imgui.set_next_window_pos(
            imgui.ImVec2(io.display_size.x - PANEL_WIDTH, top)
        )
        imgui.set_next_window_size(
            imgui.ImVec2(PANEL_WIDTH, io.display_size.y - top)
        )
        imgui.begin(
            "Game",
            flags=imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_resize
            | imgui.WindowFlags_.no_collapse,
        )
        board: HanoiGame = self.shown_game()
        imgui.text_wrapped(
            f"Goal: move all {self.session.num_disks} discs to peg 3"
        )
        imgui.text(
            f"Moves: {board.current_moves} / optimal {self.session.min_moves()}"
        )
        if board.check_win_condition():
            imgui.same_line()
            imgui.text_colored(imgui.ImVec4(0.3, 0.9, 0.3, 1.0), "-- solved!")
        if self.session.labelling != Labelling.ONE_TWO_THREE:
            imgui.text(
                "Labels on physical pegs 1 2 3: %d %d %d"
                % tuple(self._label(p) for p in range(3))
            )
        if self.review_count is None:
            imgui.text_wrapped(ascii_text(self.session.valid_moves_str()))
        if self.status:
            imgui.text_wrapped(ascii_text(self.status))

        imgui.separator()
        imgui.text("Move (current labels):")
        legal: set[tuple[int, int]] = self.legal_label_moves()
        solved: bool = board.check_win_condition()
        index: int
        pair: tuple[int, int]
        for index, pair in enumerate(MOVE_PAIRS):
            if index % 2:
                imgui.same_line()
            imgui.begin_disabled(solved or pair not in legal)
            if imgui.button(f"{pair[0]} -> {pair[1]}", imgui.ImVec2(80, 0)):
                self.make_move(*pair)
            imgui.end_disabled()

        imgui.separator()
        moves: list[tuple[int, int]] = list(self.session.recorder.default_moves)
        imgui.text(
            f"History: {len(moves)} moves (optimal {self.session.min_moves()},"
            " default 1-2-3 labels)"
        )
        imgui.begin_child(
            "history", imgui.ImVec2(0, 150), imgui.ChildFlags_.borders
        )
        if not moves:
            imgui.text_disabled("(no moves yet)")
        line: str
        for index, line in enumerate(format_move_tally(moves)):
            clicked: bool
            clicked, _selected = imgui.selectable(
                f"{line}##history{index}", self.review_count == index + 1
            )
            if clicked:
                self.review_move(index + 1)
        imgui.end_child()
        if self.review_count is not None and imgui.button("Back to current"):
            self.review_count = None
            self.pending = None
            self.status = ""
        if self.view is not None:
            imgui.separator()
            self._rebinding_view(self.view)
        imgui.end()

    def _rebinding_view(self, view: RebindingView) -> None:
        """The three-panel view as one table (so the columns scroll
        together): click a move to select its row, and the key marks the two
        bindings it uses; under the default labelling, just the moves."""
        imgui.text(view.title)
        if view.labelling == Labelling.ONE_TWO_THREE:
            imgui.text_disabled("(default labelling: no rebinding)")
            line: str
            for line in format_move_tally(view.moves):
                imgui.text(line)
        elif imgui.begin_table(
            "rebinding",
            3,
            imgui.TableFlags_.borders
            | imgui.TableFlags_.sizing_stretch_prop
            | imgui.TableFlags_.scroll_y,
            imgui.ImVec2(0, 200),
        ):
            imgui.table_setup_column(view.left_header)
            imgui.table_setup_column("Rebinding")
            imgui.table_setup_column("Rebound (pegs)")
            imgui.table_headers_row()
            key: tuple[tuple[int, int], ...] = rebinding(view.labelling)
            rebound: tuple[tuple[int, int], ...] = rebound_moves(
                view.moves, view.labelling
            )
            used: tuple[int, ...] = (
                view.moves[view.selected] if view.selected is not None else ()
            )
            row: int
            for row in range(max(len(view.moves), len(key))):
                imgui.table_next_row()
                imgui.table_set_column_index(0)
                if row < len(view.moves):
                    clicked: bool
                    clicked, _selected = imgui.selectable(
                        f"{row + 1}: {view.moves[row][0]} -> "
                        f"{view.moves[row][1]}##rebind{row}",
                        view.selected == row,
                        imgui.SelectableFlags_.span_all_columns,
                    )
                    if clicked:
                        view.selected = row
                imgui.table_set_column_index(1)
                if row < len(key):
                    # ">" marks the two bindings the selected move uses (the
                    # built-in font has no arrowhead glyph).
                    marker: str = ">" if key[row][0] in used else " "
                    imgui.text(
                        f"{marker} label {key[row][0]} -> peg {key[row][1]}"
                    )
                imgui.table_set_column_index(2)
                if row < len(rebound):
                    imgui.text(
                        f"{row + 1}: {rebound[row][0]} -> {rebound[row][1]}"
                    )
            imgui.end_table()
        if imgui.button("Dismiss"):
            self.view = None

    def _popups(self) -> None:
        """Open the popups requested since the last frame, then draw each
        modal: illegal move, save recipe, first win, save before discard,
        How to Play, and continue-from-here."""
        name: str
        for name in self.popups_to_open:
            imgui.open_popup(name)
        self.popups_to_open = []
        centre: imgui.ImVec2 = imgui.get_main_viewport().get_center()
        flags: int = imgui.WindowFlags_.always_auto_resize

        imgui.set_next_window_pos(
            centre, imgui.Cond_.appearing, imgui.ImVec2(0.5, 0.5)
        )
        if imgui.begin_popup_modal("Illegal move", None, flags)[0]:
            imgui.text(ascii_text(self.illegal_message))
            if imgui.button("OK"):
                imgui.close_current_popup()
            imgui.end_popup()

        imgui.set_next_window_pos(
            centre, imgui.Cond_.appearing, imgui.ImVec2(0.5, 0.5)
        )
        if imgui.begin_popup_modal("Save recipe", None, flags)[0]:
            imgui.text("Name this recipe:")
            _changed: bool
            _changed, self.recipe_name = imgui.input_text(
                "##name", self.recipe_name
            )
            if imgui.button("Save") and self.recipe_name.strip():
                self.save_recipe(self.recipe_name.strip())
                imgui.close_current_popup()
            imgui.same_line()
            if imgui.button("Cancel"):
                imgui.close_current_popup()
            imgui.end_popup()

        imgui.set_next_window_pos(
            centre, imgui.Cond_.appearing, imgui.ImVec2(0.5, 0.5)
        )
        if imgui.begin_popup_modal("You solved it!", None, flags)[0]:
            line: str
            for line in self.win_lines:
                imgui.text(line)
            imgui.separator()
            if imgui.button("Got it"):
                imgui.close_current_popup()
            imgui.end_popup()

        imgui.set_next_window_pos(
            centre, imgui.Cond_.appearing, imgui.ImVec2(0.5, 0.5)
        )
        if imgui.begin_popup_modal("Save solution?", None, flags)[0]:
            imgui.text("Save your solution as a recipe before starting over?")
            save: bool = imgui.button("Save")
            imgui.same_line()
            discard: bool = imgui.button("Don't save")
            if save:
                self.save_recipe(default_recipe_name(self.session.num_disks))
            if (save or discard) and self.pending_new_game is not None:
                self.new_game(self.pending_new_game)
            if save or discard:
                imgui.close_current_popup()
            imgui.end_popup()

        imgui.set_next_window_pos(
            centre, imgui.Cond_.appearing, imgui.ImVec2(0.5, 0.5)
        )
        if imgui.begin_popup_modal("How to Play", None, flags)[0]:
            imgui.text(ascii_text(HOWTO_TEXT))
            imgui.separator()
            imgui.text(
                "Drag a top disc to another peg, or use the move buttons."
            )
            imgui.text(
                "Drag the background (or the right button) to turn the"
                " camera; the wheel zooms."
            )
            if imgui.button("Got it"):
                imgui.close_current_popup()
            imgui.end_popup()

        imgui.set_next_window_pos(
            centre, imgui.Cond_.appearing, imgui.ImVec2(0.5, 0.5)
        )
        if imgui.begin_popup_modal("Continue from here?", None, flags)[0]:
            count: int = self.review_count or 0
            total: int = len(self.session.recorder.default_moves)
            later: str = (
                f"move {total}"
                if count + 1 == total
                else f"moves {count + 1}-{total}"
            )
            imgui.text(f"Continue from move {count}? This deletes {later}.")
            if imgui.button("Yes"):
                self.continue_from_review()
                imgui.close_current_popup()
            imgui.same_line()
            if imgui.button("No"):
                self.pending = None
                imgui.close_current_popup()
            imgui.end_popup()

    def frame(self, dt: float) -> None:
        """One frame: the imgui interface, board input, the moving disc, the
        3D board, then imgui on top (the caller swaps buffers)."""
        imgui.new_frame()
        self._menu_bar()
        self._panel()
        self._popups()
        self._board_input()
        self.update(dt)
        self.draw_board()
        if not self.show_pick_buffer:
            self._draw_peg_labels()
        imgui.render()


def main(argv: Sequence[str] = ()) -> None:
    """Open the window and run the 3D game until it is closed."""
    if not glfw.init():
        sys.exit("hanoi-gl: could not initialise GLFW")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)  # macOS needs it
    window: "GLFWWindow" = glfw.create_window(
        1280, 800, "Towers of Hanoi 3D", None, None
    )
    if not window:
        glfw.terminate()
        sys.exit("hanoi-gl: could not open an OpenGL 3.3 core window")
    glfw.make_context_current(window)
    glfw.swap_interval(1)
    # macOS core profiles reject drawing with VAO 0 bound; keep a default one.
    GL.glBindVertexArray(GL.glGenVertexArrays(1))
    imgui.create_context()
    renderer: GlfwRenderer = GlfwRenderer(window)
    app: HanoiGL = HanoiGL(window)
    previous: float = glfw.get_time()
    while not glfw.window_should_close(window) and not app.want_quit:
        glfw.poll_events()
        renderer.process_inputs()
        now: float = glfw.get_time()
        app.frame(now - previous)
        previous = now
        renderer.render(imgui.get_draw_data())
        glfw.swap_buffers(window)
    renderer.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    main(sys.argv[1:])
