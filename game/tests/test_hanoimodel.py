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


import hanoigame.hanoimodel


def test_postinit():
    game = hanoigame.hanoimodel.HanoiGame(num_disks=3)
    assert game.num_disks == 3
    assert game.current_moves == 0
    assert game.towers == [[3, 2, 1], [], []]


def test_makemove():
    game = hanoigame.hanoimodel.HanoiGame(num_disks=3)
    assert list(game.valid_moves()) == [(0, 1), (0, 2)]
    game.make_move(0, 1)
    assert game.towers == [[3, 2], [1], []]
    assert list(game.valid_moves()) == [(0, 2), (1, 0), (1, 2)]
    game.make_move(1, 2)
    assert game.towers == [[3, 2], [], [1]]
    assert list(game.valid_moves()) == [(0, 1), (2, 0), (2, 1)]
    game.make_move(0, 1)
    assert game.towers == [[3], [2], [1]]
    assert list(game.valid_moves()) == [(1, 0), (2, 0), (2, 1)]
    game.make_move(2, 1)
    assert game.towers == [[3], [2, 1], []]
    assert list(game.valid_moves()) == [(0, 2), (1, 0), (1, 2)]
