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

"""Recursive Towers-of-Hanoi solvers, unrolled for teaching.

Shows the recursion one level at a time: :func:`hanoi_1` through
:func:`hanoi_4` are the base case and three hand-unrolled levels, each written
in terms of the one below it, and :func:`hanoi_n` is the general recursive
form. Every solver returns its moves as a newline-separated string of
``"from -> to"`` lines. The ``@snoop()`` decorator traces each call so a
learner can watch the recursion unfold.

Each ``hanoi_*`` function takes the same three peg arguments, ``i`` (initial),
``t`` (temporary/spare) and ``g`` (goal).

Standalone teaching module: nothing in the game imports it (the playable
frontends use `hanoimodel`/`engine`). Run it directly or read it for the
algorithm.
"""

from pysnooper import snoop


@snoop()
def hanoi_1(i: int, t: int, g: int) -> str:
    """Solve a one-disc tower: the single move from the initial to the goal peg.

    This is the recursion's base case.

    Args:
        i: The initial peg number.
        t: The temporary (spare) peg number; unused for a single disc.
        g: The goal peg number.

    Returns:
        The one move as ``"i -> g"``.

    >>> print(hanoi_1(i=1,t=2,g=3))
    1 -> 3
    """

    return str(i) + " -> " + str(g)


@snoop()
def hanoi_2(i: int, t: int, g: int) -> str:
    """Solve a two-disc tower by unrolling the recursion one level.

    Moves the top disc to the spare peg, the big disc to the goal, then the
    top disc onto the goal — each step delegated to :func:`hanoi_1`.

    Args:
        i: The initial peg number.
        t: The temporary (spare) peg number.
        g: The goal peg number.

    Returns:
        The three moves as a newline-separated string.

    >>> print(hanoi_2(i=1,t=2,g=3))
    1 -> 2
    1 -> 3
    2 -> 3
    """
    two_minus_1_i_to_t: str = hanoi_1(i=i, t=g, g=t)
    big_peg_to_goal: str = hanoi_1(i=i, t=t, g=g)
    two_minus_1_t_to_g: str = hanoi_1(i=t, t=i, g=g)

    moves: str = (
        two_minus_1_i_to_t + "\n" + big_peg_to_goal + "\n" + two_minus_1_t_to_g
    )
    return moves


@snoop()
def hanoi_3(i: int, t: int, g: int) -> str:
    """Solve a three-disc tower by unrolling the recursion one more level.

    Moves the top two discs to the spare peg (via :func:`hanoi_2`), the big
    disc to the goal (via :func:`hanoi_1`), then the two discs onto the goal.

    Args:
        i: The initial peg number.
        t: The temporary (spare) peg number.
        g: The goal peg number.

    Returns:
        The seven moves as a newline-separated string.

    >>> print(hanoi_3(i=1,t=2,g=3))
    1 -> 3
    1 -> 2
    3 -> 2
    1 -> 3
    2 -> 1
    2 -> 3
    1 -> 3
    """
    three_minus_1_i_to_t: str = hanoi_2(i=i, t=g, g=t)
    big_peg_to_goal: str = hanoi_1(i=i, t=t, g=g)
    three_minus_1_t_to_g: str = hanoi_2(i=t, t=i, g=g)

    moves: str = (
        three_minus_1_i_to_t
        + "\n"
        + big_peg_to_goal
        + "\n"
        + three_minus_1_t_to_g
    )
    return moves


@snoop()
def hanoi_4(i: int, t: int, g: int) -> str:
    """Solve a four-disc tower, the last hand-unrolled level.

    Moves the top three discs to the spare peg (via :func:`hanoi_3`), the big
    disc to the goal (via :func:`hanoi_1`), then the three discs onto the goal.

    Args:
        i: The initial peg number.
        t: The temporary (spare) peg number.
        g: The goal peg number.

    Returns:
        The fifteen moves as a newline-separated string.
    """
    four_minus_1_i_to_t: str = hanoi_3(i=i, t=g, g=t)
    big_peg_to_goal: str = hanoi_1(i=i, t=t, g=g)
    four_minus_1_t_to_g: str = hanoi_3(i=t, t=i, g=g)

    moves: str = (
        four_minus_1_i_to_t
        + "\n"
        + big_peg_to_goal
        + "\n"
        + four_minus_1_t_to_g
    )
    return moves


def hanoi_n(n: int, i: int, t: int, g: int) -> str:
    """Solve an ``n``-disc tower with the general recursive algorithm.

    The pattern the ``hanoi_1`` .. ``hanoi_4`` unrollings make explicit: move
    ``n-1`` discs to the spare peg, move the big disc to the goal, then move
    the ``n-1`` discs onto the goal.

    Args:
        n: The number of discs; assumed to be at least 1.
        i: The initial peg number.
        t: The temporary (spare) peg number.
        g: The goal peg number.

    Returns:
        The ``2**n - 1`` moves as a newline-separated string.
    """
    if n == 1:
        return str(i) + " -> " + str(g)
    else:
        n_minus_1_i_to_t: str = hanoi_n(n=n - 1, i=i, t=g, g=t)
        big_peg_to_goal: str = hanoi_n(n=1, i=i, t=t, g=g)
        n_minus_1_t_to_g: str = hanoi_n(n=n - 1, i=t, t=i, g=g)

        moves: str = (
            n_minus_1_i_to_t + "\n" + big_peg_to_goal + "\n" + n_minus_1_t_to_g
        )
        return moves


if __name__ == "__main__":
    print(hanoi_n(n=4, i=1, t=2, g=3))
