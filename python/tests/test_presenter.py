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

"""Tests for the presenter: layout maths, labelling, and board rendering."""

from hanoigame.hanoimodel import HanoiGame, ValidMove
from hanoigame.presenter import (
    Labelling,
    change_labels_on_pegs,
    disk_char_width,
    label_to_tower,
    labelling_for,
    labels_to_towers,
    min_cols,
    padding_left,
    peg_center_x,
    peg_color,
    peg_gap,
    peg_visual_width,
    render,
    render_with_legend,
    total_width,
)

# --- Layout maths ---------------------------------------------------------


def test_layout_maths_3_discs() -> None:
    """Layout dimensions for a 3-disc board match the expected geometry."""
    assert peg_visual_width(3) == 5
    assert peg_gap() == 5
    assert total_width(3) == 25  # (5+5)*3 - 5
    assert peg_center_x(3, 0) == 2
    assert peg_center_x(3, 1) == 12
    assert peg_center_x(3, 2) == 22
    assert disk_char_width(1) == 1
    assert disk_char_width(2) == 3
    assert disk_char_width(3) == 5
    assert padding_left(3, 1) == 2
    assert padding_left(3, 2) == 1
    assert padding_left(3, 3) == 0
    assert min_cols(3) == 29  # total_width + 4


def test_layout_maths_5_discs() -> None:
    """Layout dimensions scale correctly for a 5-disc board."""
    assert peg_visual_width(5) == 9
    assert total_width(5) == 37  # (9+5)*3 - 5
    assert peg_center_x(5, 0) == 4
    assert peg_center_x(5, 1) == 18
    assert peg_center_x(5, 2) == 32


# --- Labelling ------------------------------------------------------------


def test_change_labels_default() -> None:
    """Under the default labelling each peg maps to itself."""
    L: Labelling = Labelling.ONE_TWO_THREE
    assert change_labels_on_pegs(L, 0) == 0
    assert change_labels_on_pegs(L, 1) == 1
    assert change_labels_on_pegs(L, 2) == 2


def test_change_labels_swap_two_three() -> None:
    """Swapping labels 2 and 3 swaps pegs 1 and 2, leaving peg 0 fixed."""
    L: Labelling = Labelling.ONE_THREE_TWO
    # physical peg 0 -> label 1, peg 1 -> label 3, peg 2 -> label 2
    assert change_labels_on_pegs(L, 0) == 0
    assert change_labels_on_pegs(L, 1) == 2
    assert change_labels_on_pegs(L, 2) == 1


def test_labelling_for_round_trip() -> None:
    """Each label triple resolves back to its matching Labelling."""
    labels: tuple[int, int, int]
    expected: Labelling
    for labels, expected in [
        ((1, 2, 3), Labelling.ONE_TWO_THREE),
        ((1, 3, 2), Labelling.ONE_THREE_TWO),
        ((2, 1, 3), Labelling.TWO_ONE_THREE),
        ((2, 3, 1), Labelling.TWO_THREE_ONE),
        ((3, 1, 2), Labelling.THREE_ONE_TWO),
        ((3, 2, 1), Labelling.THREE_TWO_ONE),
    ]:
        assert labelling_for(labels) == expected


def test_labelling_for_invalid() -> None:
    """Non-permutation label triples yield None."""
    assert labelling_for((1, 1, 1)) is None
    assert labelling_for((1, 2)) is None
    assert labelling_for((4, 1, 2)) is None


def test_label_to_tower_inverse() -> None:
    """`label_to_tower` inverts a labelling and rejects out-of-range labels."""
    L: Labelling = Labelling.ONE_THREE_TWO  # towers carry labels 1, 3, 2
    assert label_to_tower(L, 1) == 0
    assert label_to_tower(L, 3) == 1
    assert label_to_tower(L, 2) == 2
    assert label_to_tower(L, 4) is None
    assert label_to_tower(L, 0) is None


def test_labels_to_towers() -> None:
    """A (from_label, to_label) pair maps to the right physical peg pair."""
    L: Labelling = Labelling.ONE_THREE_TWO  # towers carry labels 1, 3, 2
    # User typing "1 3" wants label 1 -> label 3 = physical 0 -> physical 1
    assert labels_to_towers(L, 1, 3) == (0, 1)
    # "2 1" = label 2 -> label 1 = physical 2 -> physical 0
    assert labels_to_towers(L, 2, 1) == (2, 0)
    assert labels_to_towers(L, 1, 9) is None


def test_peg_color_follows_label_not_tower() -> None:
    """A peg's colour tracks its label across relabellings, not its position."""
    # Colour stays attached to the *label* across relabellings so the
    # student can keep tracking "label 1 is the blue peg".
    blue: int = peg_color(Labelling.ONE_TWO_THREE, 0)  # tower 0 carries label 1
    assert (
        peg_color(Labelling.TWO_ONE_THREE, 1) == blue
    )  # tower 1 carries label 1
    assert (
        peg_color(Labelling.THREE_TWO_ONE, 2) == blue
    )  # tower 2 carries label 1


# --- Rendering ------------------------------------------------------------


def test_render_3_disc_fresh_game() -> None:
    """A fresh 3-disc board renders every disc stacked on peg 1."""
    game: HanoiGame = HanoiGame(num_disks=3)
    lines: list[str] = render(game, Labelling.ONE_TWO_THREE)
    assert lines == [
        "  |         |         |  ",
        "  *         |         |  ",
        " ***        |         |  ",
        "*****       |         |  ",
        "=========================",
        "  1         2         3  ",
    ]


def test_render_after_one_move() -> None:
    """Moving the smallest disc updates only the affected pegs in the render."""
    game: HanoiGame = HanoiGame(num_disks=3)
    # Move disc 1 from peg 0 to peg 2
    moves: list[ValidMove] = list(game.move_options())
    [m for m in moves if m.move.from_peg == 0 and m.move.to_peg == 2][
        0
    ].action()
    lines: list[str] = render(game, Labelling.ONE_TWO_THREE)
    assert lines == [
        "  |         |         |  ",
        "  |         |         |  ",
        " ***        |         |  ",
        "*****       |         *  ",
        "=========================",
        "  1         2         3  ",
    ]


def test_render_label_digits_change_with_labelling() -> None:
    """A non-default labelling shows active labels above the default row."""
    game: HanoiGame = HanoiGame(num_disks=3)
    lines: list[str] = render(game, Labelling.THREE_TWO_ONE)
    # When relabelled, the active labelling row sits second-from-last and
    # the default '1 2 3' reference row sits last.
    assert lines[-2] == "  3         2         1  "
    assert lines[-1] == "  1         2         3  "


def test_render_omits_default_reference_row_under_default_labelling() -> None:
    """Under the default labelling no extra reference row is appended."""
    game: HanoiGame = HanoiGame(num_disks=3)
    lines: list[str] = render(game, Labelling.ONE_TWO_THREE)
    # n + 3 lines: board (n+1) + base + label row. No reference row needed
    # because the active labelling is already the default.
    assert len(lines) == 3 + 3
    assert lines[-1] == "  1         2         3  "


def test_render_appends_default_reference_row_when_relabelled() -> None:
    """A relabelled board appends the default '1 2 3' reference row."""
    game: HanoiGame = HanoiGame(num_disks=3)
    lines: list[str] = render(game, Labelling.ONE_THREE_TWO)
    # n + 4 lines: board (n+1) + base + active label row + default reference.
    assert len(lines) == 3 + 4
    assert lines[-2] == "  1         3         2  "
    assert lines[-1] == "  1         2         3  "


def test_render_dimensions() -> None:
    """Every rendered line has the expected width and count for each size."""
    n: int
    for n in (1, 2, 3, 5, 8):
        game: HanoiGame = HanoiGame(num_disks=n)
        lines: list[str] = render(game, Labelling.ONE_TWO_THREE)
        assert len(lines) == n + 3
        line: str
        for line in lines:
            assert len(line) == total_width(n)


def test_render_zero_discs_returns_empty() -> None:
    """A zero-disc game renders to no lines at all."""
    game: HanoiGame = HanoiGame(num_disks=0)
    assert render(game, Labelling.ONE_TWO_THREE) == []


def test_render_with_legend_appends_move_count() -> None:
    """The legend variant appends a running move count as its last line."""
    game: HanoiGame = HanoiGame(num_disks=2)
    lines: list[str] = render_with_legend(game, Labelling.ONE_TWO_THREE)
    assert lines[-1] == "Moves: 0"
    list(game.move_options())[0].action()
    lines = render_with_legend(game, Labelling.ONE_TWO_THREE)
    assert lines[-1] == "Moves: 1"
