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
from typing import List


@dataclass
class HanoiGame:
    """Represents a Hanoi Game"""

    towers: List = field(default_factory=lambda: [])
    num_disks: int = 0
    current_moves: int = 0

    def __post_init__(self):
        """Resets the game state with a given number of disks."""
        self.current_moves = 0
        self.towers = [[] for _ in range(3)]  # Create 3 empty pegs
        # Place disks on the first peg (Peg 0) from largest to smallest
        for i in range(self.num_disks, 0, -1):
            self.towers[0].append(i)

    def valid_moves(self):
        def is_valid_move(from_peg_idx: int, to_peg_idx: int):
            """Checks if a move is valid according to Towers of Hanoi rules."""
            if not (0 <= from_peg_idx < 3 and 0 <= to_peg_idx < 3):
                return False
            if from_peg_idx == to_peg_idx:
                return False
            if not self.towers[from_peg_idx]:  # Source peg empty
                return False
            disk_to_move = self.towers[from_peg_idx][-1]  # Get the top disk
            if (
                self.towers[to_peg_idx]
                and disk_to_move > self.towers[to_peg_idx][-1]
            ):  # Larger on smaller
                return False
            return True

        all_possible_peg_moves: List = [
            (0, 1),
            (0, 2),  # From Peg 1
            (1, 0),
            (1, 2),  # From Peg 2
            (2, 0),
            (2, 1),  # From Peg 3
        ]

        for from_p, to_p in all_possible_peg_moves:
            if is_valid_move(from_p, to_p):
                yield from_p, to_p

    def make_move(self, from_peg_idx: int, to_peg_idx: int):
        """Executes a valid move."""
        disk = self.towers[from_peg_idx].pop()
        self.towers[to_peg_idx].append(disk)
        self.current_moves += 1

    def check_win_condition(self) -> bool:
        """Checks if the game has been won."""
        return len(self.towers[2]) == self.num_disks
