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

"""Tests for the curses TUI's pure helpers (no curses window needed).

The input loop itself drives curses, but its Tab-completion is factored into
the pure `_complete_buffer`, which is what these exercise — the same candidate
logic as the CLI (`hanoigame.commands.completions`), with the TUI's fill rule
on top (single candidate in full, else the longest common prefix).
"""

from hanoigame.hanoigame import _complete_buffer

_NAMES: list[str] = ["other", "solve-2", "solve-3"]


def test_complete_buffer_single_verb_fills_fully() -> None:
    """One matching verb completes the whole token."""
    assert _complete_buffer("ap", _NAMES) == "apply"
    assert _complete_buffer("q", _NAMES) == "quit"


def test_complete_buffer_several_verbs_fill_common_prefix() -> None:
    """Several matches fill only the longest common prefix."""
    # 'save' and 'show' share 's'; it is already typed, so nothing is added.
    assert _complete_buffer("s", _NAMES) == "s"


def test_complete_buffer_recipe_name_after_apply() -> None:
    """After 'apply ', a unique name fills in; ambiguity fills the prefix."""
    assert _complete_buffer("apply o", _NAMES) == "apply other"
    assert _complete_buffer("apply solve-", _NAMES) == "apply solve-"
    assert _complete_buffer("apply solve-2", _NAMES) == "apply solve-2"


def test_complete_buffer_no_match_is_unchanged() -> None:
    """No candidate leaves the line untouched."""
    assert _complete_buffer("zzz", _NAMES) == "zzz"
    # 'save ' deliberately offers no recipe names.
    assert _complete_buffer("save ot", _NAMES) == "save ot"
