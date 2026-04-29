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

"""Shared input grammar for the Hanoi game front-ends.

A `parse(line)` returns a typed Command (or ParseError) so that CLI, curses,
and wxWidgets front-ends can dispatch identically. Pure: no I/O, no state.
"""

from dataclasses import dataclass
from typing import Tuple, Union


@dataclass(frozen=True)
class MoveCmd:
    """Move the top disc from `from_label` to `to_label` (1-indexed labels
    under the current Labelling)."""

    from_label: int
    to_label: int


@dataclass(frozen=True)
class RelabelCmd:
    """Set the Labelling so that physical pegs 0,1,2 carry these
    1-indexed labels (a permutation of 1,2,3)."""

    labels: Tuple[int, int, int]


@dataclass(frozen=True)
class SaveCmd:
    """Save the most recently won game's moves as a named recipe."""

    name: str


@dataclass(frozen=True)
class ApplyCmd:
    """Replay a named recipe, translated through the current labelling."""

    name: str


@dataclass(frozen=True)
class ShowCmd:
    """Print the contents of a named recipe (each move, in order)."""

    name: str


@dataclass(frozen=True)
class ListCmd:
    """List all saved recipes."""


@dataclass(frozen=True)
class HelpCmd:
    """Show help text."""


@dataclass(frozen=True)
class QuitCmd:
    """Quit the game."""


@dataclass(frozen=True)
class EmptyCmd:
    """Blank input — front-end may redraw and re-prompt."""


@dataclass(frozen=True)
class ParseError:
    """Input couldn't be parsed; `message` explains why."""

    message: str


Command = Union[
    MoveCmd,
    RelabelCmd,
    SaveCmd,
    ApplyCmd,
    ShowCmd,
    ListCmd,
    HelpCmd,
    QuitCmd,
    EmptyCmd,
    ParseError,
]


HELP_TEXT = """\
Commands:
  <from> -> <to>   move a disc, e.g. '1 -> 3' (also accepts '1 3' or '13')
  relabel a b c    rename pegs so physical pegs 1,2,3 show as a,b,c
                   (a,b,c must be a permutation of 1,2,3)
  save <name>      save the just-won solution as a recipe
  apply <name>     replay a saved recipe under the current labelling
  show <name>      print the moves in a saved recipe
  list             list saved recipes
  help             show this help
  quit             quit the game"""


def _move_or_error(a: int, b: int) -> Command:
    if not (1 <= a <= 3 and 1 <= b <= 3):
        return ParseError(f"move labels must be 1, 2, or 3 — got {a} and {b}")
    if a == b:
        return ParseError(f"can't move from peg {a} to itself")
    return MoveCmd(a, b)


def parse(line: str) -> Command:
    """Parse one line of user input into a Command. Never raises."""
    s = line.strip()
    if not s:
        return EmptyCmd()

    lower = s.lower()
    if lower in ("quit", "q", "exit"):
        return QuitCmd()
    if lower in ("help", "h", "?"):
        return HelpCmd()
    if lower == "list":
        return ListCmd()

    # Move with explicit arrow: "1 -> 3", "1->3", with any internal spacing.
    if "->" in s:
        a, _, b = s.partition("->")
        a, b = a.strip(), b.strip()
        if a.isdigit() and b.isdigit():
            return _move_or_error(int(a), int(b))
        return ParseError(
            f"couldn't parse move {s!r} — expected '<from> -> <to>', "
            "e.g. '1 -> 3'"
        )

    # Bare two-digit move shorthand: "13" -> 1 to 3
    if s.isdigit() and len(s) == 2:
        return _move_or_error(int(s[0]), int(s[1]))

    parts = s.split()

    # Spaced two-token move: "1 3"
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return _move_or_error(int(parts[0]), int(parts[1]))

    head = parts[0].lower()

    if head == "relabel":
        if len(parts) != 4 or not all(p.isdigit() for p in parts[1:]):
            return ParseError(
                "relabel takes three labels, e.g. 'relabel 2 1 3'"
            )
        labels = tuple(int(p) for p in parts[1:])
        if sorted(labels) != [1, 2, 3]:
            return ParseError(
                f"relabel needs a permutation of 1,2,3 — got {labels}"
            )
        return RelabelCmd(labels)  # type: ignore[arg-type]

    if head == "save":
        if len(parts) < 2:
            return ParseError(
                "save needs a recipe name, e.g. 'save my-3-disc-solve'"
            )
        return SaveCmd(" ".join(parts[1:]))

    if head == "apply":
        if len(parts) < 2:
            return ParseError(
                "apply needs a recipe name, e.g. 'apply my-3-disc-solve'"
            )
        return ApplyCmd(" ".join(parts[1:]))

    if head == "show":
        if len(parts) < 2:
            return ParseError(
                "show needs a recipe name, e.g. 'show my-3-disc-solve'"
            )
        return ShowCmd(" ".join(parts[1:]))

    return ParseError(
        f"unrecognised command: {s!r}. Type 'help' for the command list."
    )
