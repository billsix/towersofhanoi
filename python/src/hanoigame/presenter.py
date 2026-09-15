# Copyright (c) 2025 William Emerison Six
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""UI-agnostic rendering and labelling for HanoiGame.

This module owns the board layout maths, the peg-relabelling enum, and the
pure-text `render()` that turns a game state into ASCII lines. Curses uses
the layout helpers and the labelling table directly so it can colour cells
itself; the CLI front-end (step 2) consumes `render()` output unchanged.
"""

from collections.abc import Sequence
from enum import Enum, auto

from .hanoimodel import HanoiGame

# --- Labelling --------------------------------------------------------------


class Labelling(Enum):
    """The six ways the three pegs can be labelled 1, 2, 3.

    Each member names the 1-indexed labels worn by physical pegs 0, 1, 2 in
    order — e.g. `ONE_THREE_TWO` labels peg 0 as 1, peg 1 as 3, peg 2 as 2.
    """

    ONE_TWO_THREE = auto()
    ONE_THREE_TWO = auto()
    TWO_ONE_THREE = auto()
    TWO_THREE_ONE = auto()
    THREE_ONE_TWO = auto()
    THREE_TWO_ONE = auto()


_LABEL_ORDER: dict[Labelling, tuple[int, int, int]] = {
    Labelling.ONE_TWO_THREE: (0, 1, 2),
    Labelling.ONE_THREE_TWO: (0, 2, 1),
    Labelling.TWO_ONE_THREE: (1, 0, 2),
    Labelling.TWO_THREE_ONE: (1, 2, 0),
    Labelling.THREE_ONE_TWO: (2, 0, 1),
    Labelling.THREE_TWO_ONE: (2, 1, 0),
}


_LABELLING_BY_TUPLE: dict[tuple[int, int, int], Labelling] = {
    (1, 2, 3): Labelling.ONE_TWO_THREE,
    (1, 3, 2): Labelling.ONE_THREE_TWO,
    (2, 1, 3): Labelling.TWO_ONE_THREE,
    (2, 3, 1): Labelling.TWO_THREE_ONE,
    (3, 1, 2): Labelling.THREE_ONE_TWO,
    (3, 2, 1): Labelling.THREE_TWO_ONE,
}


def change_labels_on_pegs(labelling: Labelling, tower_index: int) -> int:
    """Return the 0-indexed label currently attached to `tower_index`.

    Args:
        labelling: The active labelling.
        tower_index: 0-indexed physical peg.

    Returns:
        The 0-indexed label on that peg under `labelling`.
    """
    return _LABEL_ORDER[labelling][tower_index]


def labelling_for(labels: Sequence[int]) -> Labelling | None:
    """Find the labelling under which pegs 0, 1, 2 carry `labels`.

    Args:
        labels: The 1-indexed labels for physical pegs 0, 1, 2 in order.

    Returns:
        The matching `Labelling`, or None if `labels` isn't a permutation of
        (1, 2, 3).
    """
    return _LABELLING_BY_TUPLE.get(tuple(labels))


def label_to_tower(labelling: Labelling, label: int) -> int | None:
    """Find which physical peg currently carries a 1-indexed label.

    Inverse of `change_labels_on_pegs`.

    Args:
        labelling: The active labelling.
        label: The 1-indexed label to locate.

    Returns:
        The 0-indexed physical peg wearing `label`, or None if `label` is out
        of the 1..3 range.
    """
    if not 1 <= label <= 3:
        return None
    target: int = label - 1
    tower_index: int
    lbl: int
    for tower_index, lbl in enumerate(_LABEL_ORDER[labelling]):
        if lbl == target:
            return tower_index
    return None


# --- Colours (referenced by curses; harmless to ignore from CLI) -----------

# Curses init_pair numbers used in hanoigame.py
COLOR_BLUE: int = 5
COLOR_YELLOW: int = 3
COLOR_RED: int = 4

# Colour follows the *label*, not the physical peg, so the student can keep
# tracking "label 1 is the blue peg" after relabelling.
_PEG_COLOR_BY_LABEL: tuple[int, int, int] = (
    COLOR_BLUE,
    COLOR_YELLOW,
    COLOR_RED,
)


def peg_color(labelling: Labelling, tower_index: int) -> int:
    """Curses colour-pair number for the peg at `tower_index` under `labelling`.

    Args:
        labelling: The active labelling.
        tower_index: 0-indexed physical peg.

    Returns:
        The curses `init_pair` number whose colour tracks that peg's label.
    """
    return _PEG_COLOR_BY_LABEL[change_labels_on_pegs(labelling, tower_index)]


# --- Layout maths ----------------------------------------------------------

PEG_GAP: int = 5


def peg_visual_width(num_disks: int) -> int:
    """Return the character width of a peg sized for `num_disks` discs.

    Args:
        num_disks: The game's disc count.

    Returns:
        The peg's visual width in characters.
    """
    return num_disks * 2 - 1


def peg_gap() -> int:
    """Return the fixed gap, in characters, between adjacent pegs.

    Returns:
        The peg gap width.
    """
    return PEG_GAP


def total_width(num_disks: int) -> int:
    """Return the full board width in characters for `num_disks` discs.

    Args:
        num_disks: The game's disc count.

    Returns:
        The board width spanning all three pegs and the gaps between them.
    """
    return (peg_visual_width(num_disks) + peg_gap()) * 3 - peg_gap()


def disk_char_width(size: int) -> int:
    """Return the character width of a disc of the given size.

    Args:
        size: The disc's size (1-indexed).

    Returns:
        The disc's width in characters.
    """
    return size * 2 - 1


def padding_left(num_disks: int, size: int) -> int:
    """Return the left padding that centres a disc within a peg column.

    Args:
        num_disks: The game's disc count (sets the peg width).
        size: The disc's size.

    Returns:
        The number of blank characters to the left of the disc.
    """
    return (peg_visual_width(num_disks) - disk_char_width(size)) // 2


def peg_center_x(num_disks: int, tower_index: int) -> int:
    """Column (0-indexed) of the centre of `tower_index`.

    Args:
        num_disks: The game's disc count.
        tower_index: 0-indexed physical peg.

    Returns:
        The centre column within a board of `total_width(num_disks)` columns.
    """
    return (
        tower_index * (peg_visual_width(num_disks) + peg_gap())
        + peg_visual_width(num_disks) // 2
    )


def min_cols(num_disks: int) -> int:
    """Minimum terminal width curses needs to draw the board with padding.

    Args:
        num_disks: The game's disc count.

    Returns:
        The minimum column count.
    """
    return total_width(num_disks) + 4


def min_rows(num_disks: int) -> int:
    """Minimum terminal height curses needs (board + status rows).

    Includes one row of headroom for the optional default-reference label
    row that appears under non-default labellings, so the requirement
    doesn't change mid-game when the user relabels.

    Args:
        num_disks: The game's disc count.

    Returns:
        The minimum row count.
    """
    return num_disks + 7


# --- Pure text rendering ---------------------------------------------------


def default_label_row(num_disks: int) -> str:
    """A line showing the default '1 2 3' labelling at peg-centre columns.

    Used as a second label row under the active labelling whenever the
    user has relabelled, so they can see both the current labels and the
    physical peg numbers underneath them.

    Args:
        num_disks: The game's disc count.

    Returns:
        A `total_width(num_disks)`-wide string with '1', '2', '3' at the peg
        centres and spaces elsewhere.
    """
    width: int = total_width(num_disks)
    row: list[str] = [" "] * width
    p_idx: int
    for p_idx in range(3):
        row[peg_center_x(num_disks, p_idx)] = str(p_idx + 1)
    return "".join(row)


def render(game: HanoiGame, labelling: Labelling) -> list[str]:
    """Render the board top-to-bottom as plain ASCII lines.

    Layout:
      rows 0..num_disks       — peg verticals, with discs overlaid
      row  num_disks + 1      — base line
      row  num_disks + 2      — peg labels under the active labelling
      row  num_disks + 3      — default '1 2 3' reference (only when the
                                active labelling differs from default)

    Total: num_disks + 3 lines under the default labelling, num_disks + 4
    when relabelled. Each line is `total_width(num_disks)` characters wide.
    Empty for a 0-disc game.

    Args:
        game: The game whose state is drawn.
        labelling: The labelling that sets the peg-label row.

    Returns:
        The board as a list of equal-width ASCII lines (empty for a 0-disc
        game).
    """
    n: int = game.num_disks
    if n == 0:
        return []
    width: int = total_width(n)
    grid: list[list[str]] = [[" "] * width for _ in range(n + 3)]

    # Vertical pegs (rows 0..n)
    p_idx: int
    row: int
    for p_idx in range(3):
        cx: int = peg_center_x(n, p_idx)
        for row in range(n + 1):
            grid[row][cx] = "|"

    # Discs — bottom of stack sits on row n; each next disc one row up
    # `peg`/`size` (and the `i, ch` targets below) stay inferred: the disc/peg
    # element type comes from HanoiGame.towers, not annotated here.
    pvw: int = peg_visual_width(n)
    for p_idx, peg in enumerate(game.towers):
        cx = peg_center_x(n, p_idx)
        for i, size in enumerate(peg):
            row = n - i
            disc_str: str = "*" * disk_char_width(size)
            start: int = cx - pvw // 2 + padding_left(n, size)
            for j, ch in enumerate(disc_str):
                grid[row][start + j] = ch

    # Base line
    grid[n + 1] = ["="] * width

    # Peg labels under the active labelling
    for p_idx in range(3):
        cx = peg_center_x(n, p_idx)
        grid[n + 2][cx] = str(change_labels_on_pegs(labelling, p_idx) + 1)

    lines: list[str] = ["".join(row) for row in grid]
    # Append the default reference row when the user has relabelled.
    if labelling != Labelling.ONE_TWO_THREE:
        lines.append(default_label_row(n))
    return lines


def render_with_legend(game: HanoiGame, labelling: Labelling) -> list[str]:
    """Same as `render`, but with a 'Moves: N' status line appended.

    Args:
        game: The game whose state is drawn.
        labelling: The labelling that sets the peg-label row.

    Returns:
        The `render` output with a trailing ``Moves: <count>`` line.
    """
    lines: list[str] = render(game, labelling)
    lines.append(f"Moves: {game.current_moves}")
    return lines


# --- Move translation through the current labelling ------------------------


def labels_to_towers(
    labelling: Labelling, from_label: int, to_label: int
) -> tuple[int, int] | None:
    """Translate a typed (from_label, to_label) label pair into peg indices.

    The labels are 1-indexed under `labelling`.

    Args:
        labelling: The active labelling the labels are typed under.
        from_label: 1-indexed source label.
        to_label: 1-indexed destination label.

    Returns:
        The ``(from_peg, to_peg)`` physical tower indices, or None if either
        label is out of range.
    """
    fp: int | None = label_to_tower(labelling, from_label)
    tp: int | None = label_to_tower(labelling, to_label)
    if fp is None or tp is None:
        return None
    return (fp, tp)
