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


# @snoop()
def swap_temporary_and_goal(s: str) -> str:
    """Remap temporary and goal
    transform 1 to 1
    tronsform 2 to 3
    transform 3 to 2

    >>> swap_temporary_and_goal("1 -> 2")
    '1 -> 3'
    >>> swap_temporary_and_goal("1 -> 3")
    '1 -> 2'
    >>> swap_temporary_and_goal("2 -> 3")
    '3 -> 2'
    >>> swap_temporary_and_goal("2 -> 1")
    '3 -> 1'
    >>> swap_temporary_and_goal("3 -> 1")
    '2 -> 1'
    >>> swap_temporary_and_goal("3 -> 2")
    '2 -> 3'
    """
    result: str = ""
    i: int

    for i in range(len(s)):
        # the temporary peg becomes the goal peg
        if s[i] == "2":
            result += "3"
        # the goal peg becomes the temporary peg
        elif s[i] == "3":
            result += "2"
        # the initial peg is unchanges
        else:
            result += s[i]
    return result


# @snoop()
def swap_initial_and_temporary(s: str) -> str:
    """Remap temporary and initial
    transform 1 to 2
    transform 2 to 1
    transform 3 to 3

    >>> swap_initial_and_temporary("1 -> 2")
    '2 -> 1'
    >>> swap_initial_and_temporary("1 -> 3")
    '2 -> 3'
    >>> swap_initial_and_temporary("2 -> 3")
    '1 -> 3'
    >>> swap_initial_and_temporary("2 -> 1")
    '1 -> 2'
    >>> swap_initial_and_temporary("3 -> 1")
    '3 -> 2'
    >>> swap_initial_and_temporary("3 -> 2")
    '3 -> 1'
    """
    result: str = ""
    i: int
    for i in range(len(s)):
        # the initial peg becomes the temporary peg
        if s[i] == "1":
            result += "2"
        # the temporary peg becomes the initial peg
        elif s[i] == "2":
            result += "1"
        else:
            result += s[i]
    return result


def hanoi(n: int):
    moves: str = "1 -> 3"

    x = 2
    while x <= n:
        x_minus_1_i_to_t: str = swap_temporary_and_goal(moves)
        big_peg_to_goal: str = moves
        x_minus_1_t_to_g: str = swap_initial_and_temporary(moves)

        moves: str = (
            x_minus_1_i_to_t + "\n" + big_peg_to_goal + "\n" + x_minus_1_t_to_g
        )
        x = x + 1
    print(moves)


if __name__ == "__main__":
    print(hanoi(4))
    # unittest.main()
