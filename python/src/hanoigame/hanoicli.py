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

"""Plain stdin/stdout front-end for HanoiGame.

Thin wrapper around `engine.GameSession`: reads a line, parses it, hands
the parsed command to the session, prints whatever lines come back. The
disc-count prompt and post-win save prompt are frontend-specific and
live here.
"""

import sys
from typing import Optional, TextIO

from . import presenter
from .commands import parse
from .engine import GameSession
from .recipe import RecipeRegistry

MAX_DISKS = 10


def _print_board(session: GameSession, out: TextIO) -> None:
    for line in presenter.render(session.game, session.labelling):
        out.write(line + "\n")
    out.write(f"Moves: {session.current_moves}\n")


def _prompt_disc_count(in_: TextIO, out: TextIO) -> Optional[int]:
    """Prompt for disc count. Returns None if user EOFs or quits."""
    while True:
        out.write(f"How many discs? (1-{MAX_DISKS}, or 'quit'): ")
        out.flush()
        line = in_.readline()
        if not line:  # EOF
            return None
        s = line.strip().lower()
        if s in ("quit", "q", "exit"):
            return None
        if s.isdigit():
            n = int(s)
            if 1 <= n <= MAX_DISKS:
                return n
        out.write(f"Please enter a number from 1 to {MAX_DISKS}.\n")


def _prompt_save(session: GameSession, in_: TextIO, out: TextIO) -> None:
    """After a win, ask whether to save this solution as a recipe."""
    out.write(
        "\nSave this solution as a recipe? "
        "Type a name, or press Enter to skip: "
    )
    out.flush()
    line = in_.readline()
    if not line:
        return
    name = line.strip()
    if not name:
        return
    out.write(session.save_recipe(name) + "\n")


def _play_game(
    n: int, registry: RecipeRegistry, in_: TextIO, out: TextIO
) -> bool:
    """Play one game. Returns True if the user wants to play again, False to
    exit the program (quit or EOF)."""
    session = GameSession(num_disks=n, registry=registry)

    while not session.is_won():
        out.write("\n")
        _print_board(session, out)
        out.write(session.valid_moves_str() + "\n")
        out.write("> ")
        out.flush()
        line = in_.readline()
        if not line:  # EOF
            return False
        result = session.dispatch(parse(line))
        for output_line in result.lines:
            out.write(output_line + "\n")
        if result.quit:
            return False

    # Won
    out.write("\n")
    _print_board(session, out)
    min_moves = session.min_moves()
    out.write(
        f"\nSolved! {session.current_moves} moves (minimum {min_moves}).\n"
    )
    if session.current_moves == min_moves:
        out.write("Optimal solution!\n")
    else:
        extra = session.current_moves - min_moves
        out.write(f"{extra} more than the minimum.\n")

    _prompt_save(session, in_, out)

    out.write("\nPlay again? (y/n): ")
    out.flush()
    again = in_.readline()
    if not again:
        return False
    return again.strip().lower().startswith("y")


def run(in_: TextIO, out: TextIO) -> int:
    """Programmatic entry point — pass any pair of streams. Returns exit code."""
    out.write("Towers of Hanoi — type 'help' for commands.\n")
    registry = RecipeRegistry()
    while True:
        n = _prompt_disc_count(in_, out)
        if n is None:
            out.write("Bye.\n")
            return 0
        if not _play_game(n, registry, in_, out):
            out.write("Bye.\n")
            return 0


def main() -> None:
    sys.exit(run(sys.stdin, sys.stdout))


if __name__ == "__main__":
    main()
