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


from pysnooper import snoop


@snoop()
def hanoi_1(i: int, t: int, g: int) -> str:
    """

    >>> print(hanoi_1(i=1,t=2,g=3))
    1 -> 3
    """

    return str(i) + " -> " + str(g)


@snoop()
def hanoi_2(i: int, t: int, g: int) -> str:
    """

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
    """

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
