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

"""Core Towers of Hanoi game state and legal-move enumeration.

This is the shared model the three front-ends (`hanoicli`, `hanoigame`,
`hanoigui`) all build on: `HanoiGame` holds the three pegs as stacks of disk
sizes, and `move_options` yields the currently legal moves each paired with a
callable that performs it. Pegs are 0-indexed here; the 1-indexed labels the
player sees are applied by `presenter`.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field


@dataclass
class Move:
    """A single disk move between two physical pegs.

    Attributes:
        from_peg: 0-indexed peg the top disk is taken from.
        to_peg: 0-indexed peg the disk is placed on.
    """

    from_peg: int
    to_peg: int


def noop() -> None:
    """Do nothing; the default `ValidMove.action` before a real one is set."""


@dataclass
class ValidMove:
    """A legal move paired with the callable that performs it.

    Attributes:
        move: The pegs the move is between.
        action: A zero-argument procedure that applies the move to the game
            (mutating the towers and the move count). Defaults to `noop`.
    """

    move: Move
    action: Callable[[], None] = field(default_factory=lambda: noop)


@dataclass
class HanoiGame:
    """A Towers of Hanoi game: three pegs holding stacks of disk sizes.

    Attributes:
        towers: The three pegs, each a list used as a stack of disk sizes
            (larger numbers are larger disks; the top of the stack is the
            list's last element).
        num_disks: The number of disks the game started with.
        current_moves: How many moves have been made so far.
    """

    towers: list[list[int]] = field(
        default_factory=lambda: [[] for _ in range(3)]
    )
    num_disks: int = 0
    current_moves: int = 0

    def __post_init__(self) -> None:
        """Stack all disks on peg 0, largest at the bottom, smallest on top."""
        for size in range(self.num_disks, 0, -1):
            self.towers[0].append(size)

    def check_win_condition(self) -> bool:
        """Return whether every disk has been moved onto peg 2 (a win)."""
        return len(self.towers[2]) == self.num_disks

    def move_options(self) -> Iterable[ValidMove]:
        """Enumerate the currently legal moves.

        Returns:
            One `ValidMove` per legal (from_peg, to_peg) pair, each carrying an
            `action` closure that, when called, pops the source peg's top disk
            onto the destination peg and increments `current_moves`.
        """

        def is_valid_move(from_peg_idx: int, to_peg_idx: int) -> bool:
            """Whether the top of `from_peg_idx` may move to `to_peg_idx`."""
            if not self.towers[from_peg_idx]:  # Source peg empty
                return False
            if (
                self.towers[to_peg_idx]
                and self.towers[from_peg_idx][-1] > self.towers[to_peg_idx][-1]
            ):  # Larger on smaller
                return False
            return True

        moves_to_return: list[ValidMove] = []
        peg_pair: tuple[int, int]
        for peg_pair in [(0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1)]:
            from_p: int
            to_p: int
            from_p, to_p = peg_pair
            if is_valid_move(from_p, to_p):

                def make_action(
                    from_peg_idx: int, to_peg_idx: int
                ) -> Callable[[], None]:
                    """Build the closure that performs one specific move."""

                    def f() -> None:
                        """Move the top disk and count it."""
                        disk: int = self.towers[from_peg_idx].pop()
                        self.towers[to_peg_idx].append(disk)
                        self.current_moves += 1

                    return f

                moves_to_return.append(
                    ValidMove(
                        Move(from_peg=from_p, to_peg=to_p),
                        action=make_action(from_p, to_p),
                    )
                )
        return moves_to_return
