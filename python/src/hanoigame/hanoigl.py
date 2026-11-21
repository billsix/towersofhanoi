"""hanoi-gl: a 3D Towers of Hanoi in OpenGL 3.3 core, with colour-ID picking.

The discs are tori and the pegs cylinders, generated in code; an orbit camera
turns around the board (drag the background, or with the right button; the
wheel zooms). It teaches **selection by colour ID**:

1. On mouse-down, the scene is drawn once more into an offscreen framebuffer
   object (FBO) that is never shown. Every pickable object (each disc) is drawn
   in one flat colour that *encodes its ID* (`id_to_rgb`); everything else
   (pegs, base) is drawn in ID 0, so it still hides the discs behind it.
2. `glReadPixels` reads the one pixel under the cursor and `rgb_bytes_to_id`
   decodes the colour back into the ID: the disc that was clicked.
3. The normal, lit frame is then drawn to the window as usual.

Press ``P`` to show the ID buffer on screen instead of the lit scene.

A picked top disc slides **up its peg until its hole clears the peg top**,
follows the cursor above the pegs, and on release slides down onto the nearest
peg. Collision detection keeps it physical: a disc moves sideways only where it
would not intersect a peg (`collides_with_peg`), so it must clear the peg top
first, and it comes down until it rests on that peg's top disc (`rest_y`). An
illegal drop (larger on smaller) slides back down its own peg, with the
reason in the window title. Moves go through the shared engine
(`engine.GameSession.dispatch`), like every other front-end.

Keys: ``1``-``8`` start a new game with that many discs, ``R`` resets the
camera, ``P`` toggles the ID-buffer view, ``Esc`` quits.

The transforms use the matrix stack of gacalc
(github.com/billsix/geometricalgebra), the same one
github.com/billsix/modelviewprojection's demos use, so the picking code can be
lifted into that book.
"""

import ctypes
import dataclasses
import enum
import math
import sys
import typing
from collections.abc import Sequence

import gacalc.gl.matrix_stack as ms
import glfw
import numpy as np
import OpenGL.GL as GL
import OpenGL.GL.shaders as shaders
from numpy.typing import NDArray

from .commands import MoveCmd
from .engine import DispatchResult, GameSession
from .recipe import RecipeRegistry

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
MAX_DISKS: int = 8
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
        GL.glBindVertexArray(0)

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


class HanoiGL:
    """The 3D board in a GLFW window: drawing, picking and moving discs.

    The event handlers (`press`, `cursor`, `release`) take window coordinates,
    so a test can drive the app without real mouse events.
    """

    def __init__(
        self, window: "GLFWWindow", num_disks: int = DEFAULT_DISKS
    ) -> None:
        """Build the GL resources for `window` (its context must be current).

        Args:
            window: The GLFW window.
            num_disks: Discs in the first game.
        """
        self.window: "GLFWWindow" = window
        self.registry: RecipeRegistry = RecipeRegistry()
        self.session: GameSession = GameSession(num_disks, self.registry)
        self.camera: OrbitCamera = OrbitCamera()
        self.moving: MovingDisc | None = None
        self.orbiting: bool = False
        self.last_cursor: tuple[float, float] = (0.0, 0.0)
        self.cursor_x: float = 0.0
        self.show_pick_buffer: bool = False
        self.message: str = "Drag a top disc to another peg."
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
        width: int
        height: int
        width, height = glfw.get_framebuffer_size(window)
        self.pick_buffer: PickBuffer = PickBuffer(width, height)
        self.disc_meshes: dict[int, Mesh] = {}
        self.peg_mesh: Mesh
        self.base_mesh: Mesh
        self._build_meshes()

    # --- Game state ------------------------------------------------------

    def new_game(self, num_disks: int) -> None:
        """Start a fresh game with `num_disks` discs; rebuild the meshes."""
        self.session = GameSession(num_disks, self.registry)
        self.moving = None
        self.message = "Drag a top disc to another peg."
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

    def _title(self) -> str:
        """The window title: the move count and the last message."""
        moves: int = self.session.current_moves
        optimal: int = self.session.min_moves()
        solved: str = " Solved!" if self.session.is_won() else ""
        return (
            f"Towers of Hanoi 3D: {moves} moves (optimal {optimal}).{solved}"
            f" {self.message}"
        )

    # --- Matrices --------------------------------------------------------

    def _set_view_projection(self) -> None:
        """Load the projection and the orbit camera's view matrix."""
        width: int
        height: int
        width, height = glfw.get_framebuffer_size(self.window)
        ms.set_to_identity_matrix(ms.MatrixStack.projection)
        ms.perspective(45.0, max(width, 1) / max(height, 1), 0.1, 100.0)
        ms.set_to_identity_matrix(ms.MatrixStack.view)
        # Read bottom-up: centre the board, turn it, tilt it, back away.
        ms.translate(ms.MatrixStack.view, 0.0, 0.0, -self.camera.distance)
        ms.rotate_x(ms.MatrixStack.view, self.camera.pitch)
        ms.rotate_y(ms.MatrixStack.view, -self.camera.yaw)
        ms.translate(ms.MatrixStack.view, 0.0, -1.2, 0.0)
        ms.set_to_identity_matrix(ms.MatrixStack.model)

    def _scene(self) -> list[tuple[Mesh, tuple[float, float, float], int, int]]:
        """Everything to draw: (mesh, position, colour index or -1, pick ID).

        Discs on the pegs come from the engine's game state (the moving disc
        is drawn where it is now, not on its peg); pegs and the base get pick
        ID 0, so they hide what is behind them but can't be picked.
        """
        items: list[tuple[Mesh, tuple[float, float, float], int, int]] = [
            (self.base_mesh, (0.0, BASE_TOP - BASE_HEIGHT, 0.0), -1, 0)
        ]
        peg: int
        for peg in range(3):
            items.append((self.peg_mesh, (peg_x(peg), BASE_TOP, 0.0), -1, 0))
        stack: list[int]
        for peg, stack in enumerate(self.session.game.towers):
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
                        size - 1,
                        size,
                    )
                )
        if self.moving is not None:
            items.append(
                (
                    self.disc_meshes[self.moving.size],
                    (self.moving.x, self.moving.y, 0.0),
                    self.moving.size - 1,
                    self.moving.size,
                )
            )
        return items

    # --- Drawing ---------------------------------------------------------

    def draw(self) -> None:
        """Draw one frame to the window: the lit scene, or the ID buffer."""
        width: int
        height: int
        width, height = glfw.get_framebuffer_size(self.window)
        GL.glViewport(0, 0, width, height)
        if self.show_pick_buffer:
            # IDs 1, 2, 3 are nearly black (1/255, 2/255, ...), so brighten
            # them for the eye; the real pick pass always uses brightness 1.
            self._draw_pick_pass(brightness=40.0)
            return
        GL.glClearColor(0.12, 0.14, 0.20, 1.0)
        # PyOpenGL's constants define no `|` for a type checker; at run time
        # they are ints.
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)  # ty: ignore[unsupported-operator]
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glUseProgram(self.lit)
        self._set_view_projection()
        mesh: Mesh
        position: tuple[float, float, float]
        colour_index: int
        for mesh, position, colour_index, _object_id in self._scene():
            with ms.push_matrix(ms.MatrixStack.model):
                ms.translate(ms.MatrixStack.model, *position)
                self._load_matrices(self.lit)
                GL.glUniform3f(
                    GL.glGetUniformLocation(self.lit, "color"),
                    *(
                        DISC_COLOURS[colour_index]
                        if colour_index >= 0
                        else WOOD
                    ),
                )
                mesh.draw()

    def _draw_pick_pass(self, brightness: float = 1.0) -> None:
        """Draw every object in its ID colour into the bound framebuffer.

        Args:
            brightness: Multiplies the ID colours; 1 (exact IDs) for picking,
                larger only to make the IDs visible on screen.
        """
        GL.glDisable(GL.GL_BLEND)
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        # PyOpenGL's constants define no `|` for a type checker; at run time
        # they are ints.
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
        for mesh, position, _colour_index, object_id in self._scene():
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

    # --- Picking ---------------------------------------------------------

    def pick_at(self, x: float, y: float) -> int:
        """The ID of the object under window point (x, y), 0 for none.

        Renders the pick pass into the offscreen framebuffer, reads back the
        one pixel under the cursor, and decodes its colour. The window is not
        touched: the next `draw` shows the normal scene.
        """
        width: int
        height: int
        width, height = glfw.get_framebuffer_size(self.window)
        if (width, height) != (self.pick_buffer.width, self.pick_buffer.height):
            self.pick_buffer.resize(width, height)
        window_width: int
        window_height: int
        window_width, window_height = glfw.get_window_size(self.window)
        # Window coordinates -> framebuffer pixels (they differ on HiDPI), and
        # flip y: GL's pixel rows count up from the bottom.
        pixel_x: int = int(x * width / max(window_width, 1))
        pixel_y: int = height - 1 - int(y * height / max(window_height, 1))
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.pick_buffer.fbo)
        GL.glViewport(0, 0, width, height)
        self._draw_pick_pass()
        GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1)
        pixel: bytes = bytes(
            GL.glReadPixels(
                pixel_x, pixel_y, 1, 1, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE
            )
        )
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        return rgb_bytes_to_id(pixel[0], pixel[1], pixel[2])

    def board_x(self, x: float, y: float) -> float:
        """Where window point (x, y) falls on the z = 0 plane the pegs stand
        in, as a world x: the cursor ray through the inverse view-projection,
        intersected with that plane."""
        window_width: int
        window_height: int
        window_width, window_height = glfw.get_window_size(self.window)
        ndc_x: float = 2.0 * x / max(window_width, 1) - 1.0
        ndc_y: float = 1.0 - 2.0 * y / max(window_height, 1)
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

    # --- Mouse handling --------------------------------------------------

    def press(self, x: float, y: float) -> None:
        """Mouse-down at (x, y): pick up a top disc, or start orbiting."""
        self.last_cursor = (x, y)
        if self.moving is not None:
            return
        picked: int = self.pick_at(x, y)
        towers: list[list[int]] = self.session.game.towers
        tops: dict[int, int] = {
            stack[-1]: peg for peg, stack in enumerate(towers) if stack
        }
        if picked == 0:
            self.orbiting = True
        elif self.session.is_won():
            self.message = "Solved! Press a number key for a new game."
        elif picked not in tops:
            self.message = f"Disc {picked} is not on top of its peg."
        else:
            source: int = tops[picked]
            self.moving = MovingDisc(
                size=picked,
                source=source,
                x=peg_x(source),
                y=rest_y(len(towers[source]) - 1),
            )
            self.cursor_x = self.moving.x
            self.message = f"Lifting disc {picked}."

    def cursor(self, x: float, y: float) -> None:
        """Mouse moved to (x, y): orbit the camera, or steer a carried disc."""
        if self.orbiting:
            self.camera.orbit(x - self.last_cursor[0], y - self.last_cursor[1])
        elif self.moving is not None and not self.moving.released:
            self.cursor_x = self.board_x(x, y)
        self.last_cursor = (x, y)

    def release(self) -> None:
        """Mouse-up: stop orbiting, or drop the carried disc on the nearest
        peg, if that move is legal; an illegal one slides back home."""
        self.orbiting = False
        if self.moving is None or self.moving.released:
            return
        moving: MovingDisc = self.moving
        target: int = nearest_peg(moving.x)
        towers: list[list[int]] = self.session.game.towers
        if (
            target != moving.source
            and towers[target]
            and (towers[target][-1] < moving.size)
        ):
            self.message = (
                f"Can't put disc {moving.size} on disc {towers[target][-1]}"
                " — larger on smaller."
            )
            target = moving.source
        moving.released = True
        moving.target = target
        resting_on: int = len(towers[target]) - (target == moving.source)
        moving.target_y = rest_y(resting_on)

    def update(self, dt: float) -> None:
        """Advance the moving disc; when it lands on another peg, make the
        move through the engine."""
        if self.moving is None:
            return
        moving: MovingDisc = self.moving
        if not moving.advance(dt, self.cursor_x, self.session.num_disks):
            return
        self.moving = None
        if moving.target == moving.source:
            return
        result: DispatchResult = self.session.dispatch(
            MoveCmd(moving.source + 1, moving.target + 1)
        )
        self.message = (
            result.lines[0]
            if result.lines
            else f"Moved {moving.source + 1} → {moving.target + 1}."
        )


def main(argv: Sequence[str] = ()) -> None:
    """Open the window and run the 3D game until it is closed."""
    if not glfw.init():
        sys.exit("hanoi-gl: could not initialise GLFW")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)  # macOS needs it
    window: "GLFWWindow" = glfw.create_window(
        1000, 700, "Towers of Hanoi 3D", None, None
    )
    if not window:
        glfw.terminate()
        sys.exit("hanoi-gl: could not open an OpenGL 3.3 core window")
    glfw.make_context_current(window)
    glfw.swap_interval(1)
    app: HanoiGL = HanoiGL(window)

    def on_mouse_button(
        _window: "GLFWWindow", button: int, action: int, _mods: int
    ) -> None:
        """Left button picks or orbits; the right button always orbits."""
        x: float
        y: float
        x, y = glfw.get_cursor_pos(window)
        match (button, action):
            case (glfw.MOUSE_BUTTON_LEFT, glfw.PRESS):
                app.press(x, y)
            case (glfw.MOUSE_BUTTON_RIGHT, glfw.PRESS):
                app.orbiting = True
                app.last_cursor = (x, y)
            case (_, glfw.RELEASE):
                app.release()
            case _:
                pass  # other buttons do nothing

    def on_key(
        _window: "GLFWWindow", key: int, _scancode: int, action: int, _mods: int
    ) -> None:
        """Digits start a new game; R resets the camera; P shows picking."""
        if action != glfw.PRESS:
            return
        if glfw.KEY_1 <= key <= glfw.KEY_0 + MAX_DISKS:
            app.new_game(key - glfw.KEY_0)
        elif key == glfw.KEY_R:
            app.camera = OrbitCamera()
        elif key == glfw.KEY_P:
            app.show_pick_buffer = not app.show_pick_buffer
        elif key == glfw.KEY_ESCAPE:
            glfw.set_window_should_close(window, True)
        else:
            pass  # other keys do nothing

    glfw.set_mouse_button_callback(window, on_mouse_button)
    glfw.set_cursor_pos_callback(window, lambda _w, x, y: app.cursor(x, y))
    glfw.set_scroll_callback(window, lambda _w, _dx, dy: app.camera.zoom(dy))
    glfw.set_key_callback(window, on_key)

    previous: float = glfw.get_time()
    while not glfw.window_should_close(window):
        glfw.poll_events()
        now: float = glfw.get_time()
        app.update(now - previous)
        previous = now
        app.draw()
        glfw.set_window_title(window, app._title())
        glfw.swap_buffers(window)
    glfw.terminate()


if __name__ == "__main__":
    main(sys.argv[1:])
