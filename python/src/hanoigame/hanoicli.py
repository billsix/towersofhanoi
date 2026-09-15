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
from typing import TextIO

from . import presenter
from .commands import Command, parse
from .engine import DispatchResult, GameSession
from .recipe import RecipeRegistry

MAX_DISKS: int = 10


def _print_board(session: GameSession, out: TextIO) -> None:
    """Render the current board plus the running move count to ``out``.

    Args:
        session: The live game session to render.
        out: The stream board lines are written to.
    """
    line: str
    for line in presenter.render(session.game, session.labelling):
        out.write(line + "\n")
    out.write(f"Moves: {session.current_moves}\n")


def _prompt_disc_count(in_: TextIO, out: TextIO) -> int | None:
    """Prompt repeatedly for a disc count until a valid one is given.

    Args:
        in_: The stream the answer is read from.
        out: The stream the prompt is written to.

    Returns:
        The chosen disc count in ``1..MAX_DISKS``, or ``None`` if the user
        EOFs or quits.
    """
    while True:
        out.write(f"How many discs? (1-{MAX_DISKS}, or 'quit'): ")
        out.flush()
        line: str = in_.readline()
        if not line:  # EOF
            return None
        s: str = line.strip().lower()
        if s in ("quit", "q", "exit"):
            return None
        if s.isdigit():
            n: int = int(s)
            if 1 <= n <= MAX_DISKS:
                return n
        out.write(f"Please enter a number from 1 to {MAX_DISKS}.\n")


def _prompt_save(session: GameSession, in_: TextIO, out: TextIO) -> None:
    """After a win, ask whether to save this solution as a recipe.

    A blank name (or EOF) skips saving; otherwise the session records the
    solution under the typed name and its confirmation line is printed.

    Args:
        session: The won session whose solution may be saved.
        in_: The stream the name is read from.
        out: The stream the prompt and result are written to.
    """
    out.write(
        "\nSave this solution as a recipe? "
        "Type a name, or press Enter to skip: "
    )
    out.flush()
    line: str = in_.readline()
    if not line:
        return
    name: str = line.strip()
    if not name:
        return
    out.write(session.save_recipe(name) + "\n")


def _play_game(
    n: int, registry: RecipeRegistry, in_: TextIO, out: TextIO
) -> bool:
    """Play one game to a win, quit, or EOF.

    Args:
        n: The number of discs to start with.
        registry: The recipe store shared across games.
        in_: The stream commands are read from.
        out: The stream the board and messages are written to.

    Returns:
        ``True`` if the user wants to play again, ``False`` to exit the
        program (quit or EOF).
    """
    session: GameSession = GameSession(num_disks=n, registry=registry)

    while not session.is_won():
        out.write("\n")
        _print_board(session, out)
        out.write(session.valid_moves_str() + "\n")
        out.write("> ")
        out.flush()
        line: str = in_.readline()
        if not line:  # EOF
            return False
        cmd: Command = parse(line)
        result: DispatchResult = session.dispatch(cmd)
        output_line: str
        for output_line in result.lines:
            out.write(output_line + "\n")
        # After a plain move under a relabelling, print the same three-column
        # rebinding table `apply` shows — so a hand move teaches the local->
        # global mapping too. Empty otherwise (see move_teaching_lines).
        teaching_line: str
        for teaching_line in session.move_teaching_lines(cmd, result):
            out.write(teaching_line + "\n")
        if result.quit:
            return False

    # Won
    out.write("\n")
    _print_board(session, out)
    min_moves: int = session.min_moves()
    out.write(
        f"\nSolved! {session.current_moves} moves (minimum {min_moves}).\n"
    )
    if session.current_moves == min_moves:
        out.write("Optimal solution!\n")
    else:
        extra: int = session.current_moves - min_moves
        out.write(f"{extra} more than the minimum.\n")

    _prompt_save(session, in_, out)

    out.write("\nPlay again? (y/n): ")
    out.flush()
    again: str = in_.readline()
    if not again:
        return False
    return again.strip().lower().startswith("y")


def run(in_: TextIO, out: TextIO) -> int:
    """Programmatic entry point — pass any pair of streams.

    Loops over games, prompting for a disc count and playing until the user
    quits or EOFs.

    Args:
        in_: The stream commands are read from.
        out: The stream all output is written to.

    Returns:
        The process exit code (always ``0``).
    """
    out.write("Towers of Hanoi — type 'help' for commands.\n")
    registry: RecipeRegistry = RecipeRegistry()
    while True:
        n: int | None = _prompt_disc_count(in_, out)
        if n is None:
            out.write("Bye.\n")
            return 0
        if not _play_game(n, registry, in_, out):
            out.write("Bye.\n")
            return 0


def main() -> None:
    """Console-script entry point: run the game on real stdin/stdout."""
    sys.exit(run(sys.stdin, sys.stdout))


if __name__ == "__main__":
    main()
