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

"""Tests for the presenter.

The layout-maths, labelling-helper, move-tally, and single-board `render`
examples are doctests in `presenter.py` now (collected via --doctest-modules);
what stays here is the loop/invariant and multi-step/after-mutation cases a
doctest can't carry cleanly.
"""

from hanoigame.hanoimodel import HanoiGame, ValidMove
from hanoigame.presenter import (
    Labelling,
    labelling_for,
    render,
    render_with_legend,
    total_width,
)


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


def test_render_with_legend_appends_move_count() -> None:
    """The legend variant appends a running move count as its last line."""
    game: HanoiGame = HanoiGame(num_disks=2)
    lines: list[str] = render_with_legend(game, Labelling.ONE_TWO_THREE)
    assert lines[-1] == "Moves: 0"
    list(game.move_options())[0].action()
    lines = render_with_legend(game, Labelling.ONE_TWO_THREE)
    assert lines[-1] == "Moves: 1"
