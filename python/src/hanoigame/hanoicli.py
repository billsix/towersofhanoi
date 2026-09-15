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

At an interactive terminal, `readline` tab-completion is installed (command
verbs at the start of a line; saved-recipe names after ``apply ``/``show ``).
When driven from an injected stream (pipes, tests) the reads fall back to
`stream.readline()` unchanged, so scripted I/O stays byte-for-byte identical.
"""

import sys
from typing import TextIO

from . import presenter
from .commands import COMMAND_VERBS, Command, parse
from .engine import DispatchResult, GameSession
from .recipe import RecipeRegistry

MAX_DISKS: int = 10


def _is_interactive(in_: TextIO) -> bool:
    """Return whether we are reading from the real interactive terminal.

    Only then do `input()`/`readline` editing and completion apply; an injected
    or piped stream is not interactive, so its I/O path stays untouched.

    Args:
        in_: The stream the caller reads from.
    """
    if in_ is not sys.stdin:
        return False
    try:
        return sys.stdin.isatty()
    except (OSError, ValueError):
        return False


def _read_line(prompt: str, in_: TextIO, out: TextIO) -> str | None:
    """Read one line of input, with terminal editing when interactive.

    At an interactive terminal the read goes through `input()` so `readline`
    line-editing and tab-completion fire; otherwise it writes `prompt` to `out`
    and reads `in_` exactly as before, keeping scripted output identical.

    Args:
        prompt: The prompt to display before reading.
        in_: The stream the line is read from.
        out: The stream the prompt is written to (non-interactive path).

    Returns:
        The line with its trailing newline stripped, or ``None`` on EOF.
    """
    if _is_interactive(in_):
        out.flush()
        try:
            return input(prompt)
        except EOFError:
            return None
    out.write(prompt)
    out.flush()
    line: str = in_.readline()
    if not line:  # EOF
        return None
    return line.rstrip("\n")


def _completions(buffer: str, text: str, registry: RecipeRegistry) -> list[str]:
    """Candidate completions for `text` given the whole input line `buffer`.

    Command verbs while still on the first token; saved-recipe names after
    ``apply ``/``show `` (the load side). Deliberately nothing after other verbs
    — notably ``save ``, so completion never suggests overwriting an existing
    recipe. Pure: no `readline`, no I/O, so it is unit-testable on its own.

    Args:
        buffer: The whole line being edited (`readline.get_line_buffer()`).
        text: The partial word `readline` wants completions for.
        registry: The recipe store, queried for names on the load side.

    Returns:
        The matching completion candidates, in display order.
    """
    stripped: str = buffer.lstrip()
    if stripped.startswith(("apply ", "show ")):
        return [name for name in registry.names() if name.startswith(text)]
    if " " in stripped:
        return []
    return [verb for verb in COMMAND_VERBS if verb.startswith(text)]


def _install_completion(registry: RecipeRegistry, in_: TextIO) -> None:
    """Install the readline tab-completer, but only at a real terminal.

    A no-op when `readline` is unavailable or the input is not interactive, so
    the scripted/piped path never touches readline. Binds Tab for both GNU
    readline and macOS's libedit.

    Args:
        registry: The recipe store the completer reads names from (shared, so
            names saved mid-session complete on later lines).
        in_: The input stream; completion is installed only if it is the
            interactive terminal.
    """
    if not _is_interactive(in_):
        return
    try:
        import readline
    except ImportError:
        return

    def completer(text: str, state: int) -> str | None:
        """readline completion hook: the `state`-th match, or None."""
        options: list[str] = _completions(
            readline.get_line_buffer(), text, registry
        )
        return options[state] if state < len(options) else None

    readline.set_completer(completer)
    if "libedit" in (readline.__doc__ or ""):
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")


def _print_board(session: GameSession, out: TextIO) -> None:
    """Render the current board plus the running move count to ``out``.

    Args:
        session: The live game session to render.
        out: The stream board lines are written to.
    """
    line: str
    for line in presenter.render_with_legend(session.game, session.labelling):
        out.write(line + "\n")


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
        line: str | None = _read_line(
            f"How many discs? (1-{MAX_DISKS}, or 'quit'): ", in_, out
        )
        if line is None:  # EOF
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
    """After a win, offer to save this solution as a recipe.

    Pressing Enter accepts the default name ``solve-<n>`` (matching the GUI, so
    the user needn't invent one); typing a name saves under it; typing ``-``
    (or EOF) skips saving.

    Args:
        session: The won session whose solution may be saved.
        in_: The stream the name is read from.
        out: The stream the prompt and result are written to.
    """
    default: str = f"solve-{session.num_disks}"
    line: str | None = _read_line(
        f"\nSave this solution as a recipe? "
        f"Enter to save as '{default}', a name to rename, or '-' to skip: ",
        in_,
        out,
    )
    if line is None:
        return
    name: str = line.strip()
    if name == "-":
        return
    if not name:
        name = default
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
        line: str | None = _read_line("> ", in_, out)
        if line is None:  # EOF
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

    again: str | None = _read_line("\nPlay again? (y/n): ", in_, out)
    if again is None:
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
    _install_completion(registry, in_)
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
