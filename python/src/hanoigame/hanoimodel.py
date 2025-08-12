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

from dataclasses import dataclass, field
from typing import Callable, Iterable, List


@dataclass
class Move:
    from_peg: int  #: The peg from which the top disk is taken
    to_peg: int  #: The peg on which the disk is placed


def noop() -> None:
    pass


@dataclass
class ValidMove:
    """Represents an option for a move in Hanoi Game"""

    move: Move  #: The pegs of the valid move
    action: Callable[[], None] = field(
        default_factory=noop
    )  #: A procedure to do the valid move


@dataclass
class HanoiGame:
    """Represents a Hanoi Game"""

    towers: List = field(
        default_factory=lambda: [[] for _ in range(3)]
    )  #: The three towers, each of which implmented using a list as a stack
    num_disks: int = field(
        default_factory=lambda: 0
    )  #: The number of disks for this game
    current_moves: int = field(
        default_factory=lambda: 0
    )  #: The number of moves done so far in this game

    def __post_init__(self):
        """Resets the game state with a given number of disks."""
        # Place disks on the first peg (Peg 0) from largest to smallest
        for i in range(self.num_disks, 0, -1):
            self.towers[0].append(i)

    def check_win_condition(self) -> bool:
        """Checks if the game has been won."""
        return len(self.towers[2]) == self.num_disks

    def move_options(self) -> Iterable[ValidMove]:
        """
        Returns an iterable which represents the valid moves

        The first element of the tuple is a tuple that represents
        the from-peg and to-peg

        The second element of the tuple is a callable of zero arguments,
        which when invoked, makes the move from the from-peg to the
        to-peg
        """

        def is_valid_move(from_peg_idx: int, to_peg_idx: int) -> bool:
            """Checks if a move is valid according to Towers of Hanoi rules."""
            if not self.towers[from_peg_idx]:  # Source peg empty
                return False
            if (
                self.towers[to_peg_idx]
                and self.towers[from_peg_idx][-1] > self.towers[to_peg_idx][-1]
            ):  # Larger on smaller
                return False
            return True

        moves_to_return: List[ValidMove] = []
        for from_p, to_p in [
            (0, 1),
            (0, 2),
            (1, 0),
            (1, 2),
            (2, 0),
            (2, 1),
        ]:
            if is_valid_move(from_p, to_p):

                def make_action(
                    from_peg_idx: int, to_peg_idx: int
                ) -> Callable[[], None]:
                    def f() -> None:
                        disk = self.towers[from_peg_idx].pop()
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

    def max_disk_size(self) -> int:
        return self.num_disks

    def peg_visual_width(self) -> int:
        return self.max_disk_size() * 2 - 1

    def peg_gap(self) -> int:
        return 5

    def total_game_content_width(self) -> int:
        gap: int = self.peg_gap()
        return (self.peg_visual_width() + gap) * 3 - gap

    def min_cols(self) -> int:
        return self.total_game_content_width() + 4  # A little padding

    def min_rows(self) -> int:
        return self.num_disks + 6  # Enough space for disks, base, messages

    # disks

    def disk_char_width(self, size: int) -> int:
        return size * 2 - 1

    def padding_left(self, size: int) -> int:
        return (self.peg_visual_width() - self.disk_char_width(size)) // 2
