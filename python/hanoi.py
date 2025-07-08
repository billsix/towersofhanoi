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

import snoop

from typing import Callable
import unittest
import doctest


# @snoop
def first_remap(s: str) -> str:
    """Remap temporary and goal
    1->1
    2->3
    3->2

    >>> first_remap("1 -> 2")
    '1 -> 3'
    >>> first_remap("1 -> 3")
    '1 -> 2'
    >>> first_remap("2 -> 3")
    '3 -> 2'
    >>> first_remap("2 -> 1")
    '3 -> 1'
    >>> first_remap("3 -> 1")
    '2 -> 1'
    >>> first_remap("3 -> 2")
    '2 -> 3'
    """
    result: str = ""
    c: str
    for c in s:
        # the temporary peg becomes the goal peg
        if c == "2":
            result += "3"
        # the goal peg becomes the temporary peg
        elif c == "3":
            result += "2"
        # the initial peg is unchanges
        else:
            result += c
    return result


# @snoop
def second_remap(s: str) -> str:
    """Remap temporary and initial
    1->2
    2->1
    3->3

    >>> second_remap("1 -> 2")
    '2 -> 1'
    >>> second_remap("1 -> 3")
    '2 -> 3'
    >>> second_remap("2 -> 3")
    '1 -> 3'
    >>> second_remap("2 -> 1")
    '1 -> 2'
    >>> second_remap("3 -> 1")
    '3 -> 2'
    >>> second_remap("3 -> 2")
    '3 -> 1'
    """
    result: str = ""
    c: str
    for c in s:
        # the initial peg becomes the temporary peg
        if c == "1":
            result += "2"
        # the temporary peg becomes the initial peg
        elif c == "2":
            result += "1"
        else:
            result += c
    return result


@snoop
def hanoi(n: int):
    moves: str = "1 -> 3"

    x = 2
    while x <= n:
        x_minus_1_i_to_t: str = first_remap(moves)
        big_peg_to_goal: str = "1 -> 3"
        x_minus_1_t_to_g: str = second_remap(moves)

        moves: str = x_minus_1_i_to_t + "\n" + big_peg_to_goal + "\n" + x_minus_1_t_to_g
        x = x + 1
    print(moves)


@snoop
def hanoi_1(i: int, t: int, g: int) -> str:
    """

    >>> print(hanoi_1(i=1,t=2,g=3))
    1 -> 3
    """

    return str(i) + " -> " + str(g)


@snoop
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

    moves: str = two_minus_1_i_to_t + "\n" + big_peg_to_goal + "\n" + two_minus_1_t_to_g
    return moves


@snoop
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
        three_minus_1_i_to_t + "\n" + big_peg_to_goal + "\n" + three_minus_1_t_to_g
    )
    return moves


@snoop
def hanoi_4(i: int, t: int, g: int) -> str:
    four_minus_1_i_to_t: str = hanoi_3(i=i, t=g, g=t)
    big_peg_to_goal: str = hanoi_1(i=i, t=t, g=g)
    four_minus_1_t_to_g: str = hanoi_3(i=t, t=i, g=g)

    moves: str = (
        four_minus_1_i_to_t + "\n" + big_peg_to_goal + "\n" + four_minus_1_t_to_g
    )
    return moves


def hanoi_3_second(i: int, t: int, g: int) -> str:
    @snoop
    def hanoi_1(i: int, t: int, g: int) -> str:
        return str(i) + " -> " + str(g)

    @snoop
    def hanoi_2(i: int, t: int, g: int, h1: Callable[[int, int, int], str]) -> str:
        two_minus_1_i_to_t: str = h1(i=i, t=g, g=t)
        big_peg_to_goal: str = h1(i=i, t=t, g=g)
        two_minus_1_t_to_g: str = h1(i=t, t=i, g=g)

        moves: str = (
            two_minus_1_i_to_t + "\n" + big_peg_to_goal + "\n" + two_minus_1_t_to_g
        )
        return moves

    @snoop
    def hanoi_3(
        i: int,
        t: int,
        g: int,
        h2: Callable[[int, int, int], str],
        h1: Callable[[int, int, int], str],
    ) -> str:
        three_minus_1_i_to_t: str = h2(i=i, t=g, g=t, h1=h1)
        big_peg_to_goal: str = h1(i=i, t=t, g=g)
        three_minus_1_t_to_g: str = h2(i=t, t=i, g=g, h1=h1)

        moves: str = (
            three_minus_1_i_to_t + "\n" + big_peg_to_goal + "\n" + three_minus_1_t_to_g
        )
        return moves

    return hanoi_3(i, t, g, hanoi_2, hanoi_1)


def hanoi_n_second(n: int, i: int, t: int, g: int) -> str:
    @snoop
    def hanoi_1(i: int, t: int, g: int) -> str:
        return str(i) + " -> " + str(g)

    @snoop
    def hanoi_n(
        n: int, i: int, t: int, g: int, h: Callable[[int, int, int], str]
    ) -> str:
        if n == 1:
            return hanoi_1(i, t, g)
        else:
            n_minus_1_i_to_t: str = h(n=n - 1, i=i, t=g, g=t, h=h)
            big_peg_to_goal: str = hanoi_1(i=i, t=t, g=g)
            n_minus_1_t_to_g: str = h(n=n - 1, i=t, t=i, g=g, h=h)

            moves: str = (
                n_minus_1_i_to_t + "\n" + big_peg_to_goal + "\n" + n_minus_1_t_to_g
            )
            return moves

    return hanoi_n(n, i, t, g, hanoi_n)


def hanoi_n_third(n: int, i: int, t: int, g: int) -> str:
    @snoop
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

    return hanoi_n(n, i, t, g)


class TestMethodFinder(unittest.TestCase):
    def test_doctest(self):
        import sys

        failureCount, testCount = doctest.testmod(sys.modules[__name__])
        self.assertEqual(0, failureCount)


if __name__ == "__main__":
    print(hanoi(3))
    unittest.main()
