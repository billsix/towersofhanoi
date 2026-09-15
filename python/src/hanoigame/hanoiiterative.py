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

"""Iterative Towers-of-Hanoi solver built by string rewriting.

Teaching companion to :mod:`hanoirecursive`. Instead of recursion, it builds
the move list for ``n`` discs by taking the ``n-1`` solution and rewriting its
peg labels twice (via :func:`swap_temporary_and_goal` and
:func:`swap_initial_and_temporary`) to retarget the two sub-towers, then
splicing the big-disc move between them.

Standalone teaching module: nothing in the game imports it (the playable
frontends use `hanoimodel`/`engine`). Run it directly or read it for the
algorithm.
"""


def swap_temporary_and_goal(s: str) -> str:
    """Rewrite a move sequence with the temporary and goal pegs swapped.

    Used to retarget the ``n-1`` sub-solution so it moves onto the temporary
    peg instead of the goal peg.

    Args:
        s: A newline-separated sequence of ``"a -> b"`` moves using the peg
            labels ``1``, ``2`` and ``3``.

    Returns:
        The same sequence with every ``2`` rewritten to ``3`` and every ``3``
        rewritten to ``2``.
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


def swap_initial_and_temporary(s: str) -> str:
    """Rewrite a move sequence with the initial and temporary pegs swapped.

    Used to retarget the ``n-1`` sub-solution so it moves off the temporary
    peg (where the smaller tower was parked) onto the goal.

    Args:
        s: A newline-separated sequence of ``"a -> b"`` moves using the peg
            labels ``1``, ``2`` and ``3``.

    Returns:
        The same sequence with every ``1`` rewritten to ``2`` and every ``2``
        rewritten to ``1``.
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


def hanoi(n: int) -> None:
    """Print the moves that solve an ``n``-disc puzzle from peg 1 to peg 3.

    Starts from the one-disc solution and, for each additional disc, rewrites
    the current move list twice to place the two ``n-1`` sub-towers around the
    big-disc move.

    Args:
        n: The number of discs; assumed to be at least 1.
    """
    moves: str = "1 -> 3"

    x: int = 2
    while x <= n:
        x_minus_1_i_to_t: str = swap_temporary_and_goal(moves)
        big_peg_to_goal: str = "1 -> 3"
        x_minus_1_t_to_g: str = swap_initial_and_temporary(moves)

        moves: str = (
            x_minus_1_i_to_t + "\n" + big_peg_to_goal + "\n" + x_minus_1_t_to_g
        )
        x = x + 1
    print(moves)


if __name__ == "__main__":
    print(hanoi(3))
    # unittest.main()
