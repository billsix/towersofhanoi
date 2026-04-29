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

import pytest

from hanoigame.commands import (
    ApplyCmd,
    EmptyCmd,
    HelpCmd,
    ListCmd,
    MoveCmd,
    ParseError,
    QuitCmd,
    RelabelCmd,
    SaveCmd,
    ShowCmd,
    parse,
)

# --- Moves ----------------------------------------------------------------


@pytest.mark.parametrize(
    "line, expected",
    [
        ("1 3", MoveCmd(1, 3)),
        ("2 1", MoveCmd(2, 1)),
        ("  1   3  ", MoveCmd(1, 3)),
        ("13", MoveCmd(1, 3)),
        ("31", MoveCmd(3, 1)),
        # Arrow form (the canonical display style)
        ("1 -> 3", MoveCmd(1, 3)),
        ("1->3", MoveCmd(1, 3)),
        ("  1->3  ", MoveCmd(1, 3)),
        ("1 ->3", MoveCmd(1, 3)),
        ("1-> 3", MoveCmd(1, 3)),
        ("3 -> 1", MoveCmd(3, 1)),
    ],
)
def test_parse_move(line, expected):
    assert parse(line) == expected


@pytest.mark.parametrize(
    "line",
    [
        "1 -> 1",  # same peg, arrow form
        "4 -> 1",  # out of range, arrow form
        "1 -> wat",  # malformed right side
        "-> 3",  # missing left side
    ],
)
def test_parse_arrow_move_invalid(line):
    assert isinstance(parse(line), ParseError)


@pytest.mark.parametrize(
    "line",
    [
        "1 1",  # same peg
        "11",
        "4 1",  # out of range
        "1 4",
        "0 3",
        "44",
    ],
)
def test_parse_move_invalid_returns_parse_error(line):
    result = parse(line)
    assert isinstance(result, ParseError)


# --- Relabel --------------------------------------------------------------


@pytest.mark.parametrize(
    "line, labels",
    [
        ("relabel 1 2 3", (1, 2, 3)),
        ("relabel 2 1 3", (2, 1, 3)),
        ("relabel 3 2 1", (3, 2, 1)),
        ("RELABEL 1 3 2", (1, 3, 2)),
    ],
)
def test_parse_relabel(line, labels):
    assert parse(line) == RelabelCmd(labels)


@pytest.mark.parametrize(
    "line",
    [
        "relabel",
        "relabel 1 2",
        "relabel 1 2 3 4",
        "relabel 1 1 1",  # not a permutation
        "relabel 1 2 4",
        "relabel a b c",
    ],
)
def test_parse_relabel_invalid(line):
    assert isinstance(parse(line), ParseError)


# --- Recipes --------------------------------------------------------------


def test_parse_save_with_name():
    assert parse("save foo") == SaveCmd("foo")


def test_parse_save_multiword_name():
    assert parse("save my 3-disc solve") == SaveCmd("my 3-disc solve")


def test_parse_save_no_name_is_error():
    assert isinstance(parse("save"), ParseError)


def test_parse_apply_with_name():
    assert parse("apply foo") == ApplyCmd("foo")


def test_parse_apply_no_name_is_error():
    assert isinstance(parse("apply"), ParseError)


def test_parse_show_with_name():
    assert parse("show foo") == ShowCmd("foo")


def test_parse_show_no_name_is_error():
    assert isinstance(parse("show"), ParseError)


def test_parse_list():
    assert parse("list") == ListCmd()
    assert parse("LIST") == ListCmd()


# --- Help / quit / empty / garbage ---------------------------------------


@pytest.mark.parametrize("line", ["help", "h", "?", "HELP"])
def test_parse_help(line):
    assert parse(line) == HelpCmd()


@pytest.mark.parametrize("line", ["quit", "q", "exit", "QUIT", "Q"])
def test_parse_quit(line):
    assert parse(line) == QuitCmd()


@pytest.mark.parametrize("line", ["", "   ", "\t", "\n"])
def test_parse_empty(line):
    assert parse(line) == EmptyCmd()


@pytest.mark.parametrize(
    "line",
    [
        "wat",
        "move 1 3",
        "1 2 3",
        "relabel-now 1 2 3",
        "saveapply foo",
    ],
)
def test_parse_garbage_returns_parse_error(line):
    assert isinstance(parse(line), ParseError)
