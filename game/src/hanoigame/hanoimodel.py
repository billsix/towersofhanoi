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
from typing import Callable, Iterable, List, Tuple


@dataclass
class HanoiGame:
    """Represents a Hanoi Game"""

    towers: List = field(default_factory=lambda: [[] for _ in range(3)])
    num_disks: int = 0
    current_moves: int = 0

    def __post_init__(self):
        """Resets the game state with a given number of disks."""
        # Place disks on the first peg (Peg 0) from largest to smallest
        for i in range(self.num_disks, 0, -1):
            self.towers[0].append(i)

    def check_win_condition(self) -> bool:
        """Checks if the game has been won."""
        return len(self.towers[2]) == self.num_disks

    def move_options(self) -> Iterable[Tuple[Tuple[int, int], Callable]]:
        """
        Returns an iterable which represents the valid moves

        The first element of the tuple is a tuple that represents
        the from-peg and to-peg

        The second element of the tuple is a callable of zero arguments,
        which when invoked, makes the move from the from-peg to the
        to-peg
        """

        def is_valid_move(from_peg_idx: int, to_peg_idx: int):
            """Checks if a move is valid according to Towers of Hanoi rules."""
            if not self.towers[from_peg_idx]:  # Source peg empty
                return False
            if (
                self.towers[to_peg_idx]
                and self.towers[from_peg_idx][-1] > self.towers[to_peg_idx][-1]
            ):  # Larger on smaller
                return False
            return True

        moves_to_return: List[Tuple[Tuple[int, int], Callable]] = []
        for from_p, to_p in [
            (0, 1),
            (0, 2),
            (1, 0),
            (1, 2),
            (2, 0),
            (2, 1),
        ]:
            if is_valid_move(from_p, to_p):

                def make_action(from_peg_idx: int, to_peg_idx: int):
                    def f():
                        disk = self.towers[from_peg_idx].pop()
                        self.towers[to_peg_idx].append(disk)
                        self.current_moves += 1

                    return f

                moves_to_return.append(
                    ((from_p, to_p), make_action(from_p, to_p))
                )
        return moves_to_return
