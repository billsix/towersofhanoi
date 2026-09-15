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

"""Curses front-end for HanoiGame.

Same command grammar and dispatcher as the CLI — the user types `1 -> 3`,
`relabel 1 3 2`, `apply foo`, `help`, `quit`, etc. into a prompt at the
bottom of the screen. The board is drawn in colour above; the most recent
result/error message sits just above the prompt.
"""

import curses
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from curses import (
    COLOR_BLACK,
    COLOR_BLUE,
    COLOR_CYAN,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    color_pair,
    curs_set,
    has_colors,
    init_pair,
    start_color,
)

from . import presenter
from .commands import Command, parse
from .engine import DispatchResult, GameSession
from .presenter import Labelling, change_labels_on_pegs, peg_color
from .recipe import RecipeRegistry

MAX_DISKS: int = 10
MSG_AREA_LINES: int = 6  # max message lines shown between board and hint
HINT_AREA_LINES: int = 2  # rows reserved for hint text above the prompt

# Default hint shown during play. The first line spells out the move
# syntax explicitly so a brand-new user knows what to type without having
# to discover the 'help' command first.
DEFAULT_HINT: list[str] = [
    "Move: type 'from -> to' (e.g. '1 -> 3')",
    "Other: relabel a b c | apply <name> | show <name> | list | help | quit",
]

# Curses colour-pair numbers
PAIR_DISC: int = 1
PAIR_DEFAULT: int = 2
PAIR_MESSAGE: int = 3
PAIR_ERROR: int = 4
PAIR_BLUE: int = 5  # also used by presenter.peg_color


@contextmanager
def stdscr_attr(stdscr: curses.window, attr: int) -> Iterator[None]:
    """Turn a curses attribute on for the body, then off again.

    Args:
        stdscr: The curses window the attribute applies to.
        attr: The attribute (e.g. a ``color_pair`` value) to enable.

    Yields:
        Control to the ``with`` block while ``attr`` is active.
    """
    stdscr.attron(attr)
    try:
        yield
    finally:
        stdscr.attroff(attr)


# --- Drawing primitives ---------------------------------------------------


def _required_rows(num_disks: int) -> int:
    """Minimum LINES needed: board (n+4 worst-case) + 1 gap + msg area +
    hint area + prompt.

    This stays curses-local (rather than using ``presenter.min_rows``) because
    it depends on this frontend's ``MSG_AREA_LINES``/``HINT_AREA_LINES`` layout,
    which the presenter has no business knowing about.
    """
    return (num_disks + 4) + 1 + MSG_AREA_LINES + HINT_AREA_LINES + 1


def _required_cols(num_disks: int) -> int:
    """Minimum terminal columns needed to draw ``num_disks`` discs."""
    return presenter.min_cols(num_disks)


def _check_size(stdscr: curses.window, num_disks: int) -> bool:
    """Return whether the terminal is large enough for the board.

    Args:
        stdscr: The curses window (unused; kept for call-site symmetry).
        num_disks: The number of discs to be drawn.

    Returns:
        ``True`` if both ``curses.LINES`` and ``curses.COLS`` meet the
        required minimums.
    """
    return curses.LINES >= _required_rows(
        num_disks
    ) and curses.COLS >= _required_cols(num_disks)


def _show_too_small(stdscr: curses.window, num_disks: int) -> None:
    """Show a 'terminal too small' notice and wait for a keypress.

    Args:
        stdscr: The curses window to draw on.
        num_disks: The number of discs, used to report the required size.
    """
    stdscr.clear()
    stdscr.addstr(
        0,
        0,
        f"Terminal too small. Need at least "
        f"{_required_rows(num_disks)} rows x "
        f"{_required_cols(num_disks)} cols. "
        f"Have {curses.LINES} x {curses.COLS}.",
    )
    stdscr.addstr(1, 0, "Resize the window and press any key.")
    stdscr.refresh()
    stdscr.getch()


def _draw_board(stdscr: curses.window, session: GameSession) -> None:
    """Draw the board centred horizontally, base above the message area.

    Renders the three pegs, the discs on them, the base line, the active
    per-peg labels and — when a relabelling is in effect — a default-reference
    row beneath.

    Args:
        stdscr: The curses window to draw on.
        session: The live game session supplying the board state.
    """
    n: int = session.num_disks
    labelling: Labelling = session.labelling
    relabelled: bool = labelling != Labelling.ONE_TWO_THREE

    start_x: int = max(0, (curses.COLS - presenter.total_width(n)) // 2)
    # base_y is the bottom row of disc slots. Below that:
    #   base_y + 1: base line
    #   base_y + 2: active label row
    #   base_y + 3: default reference row (only when relabelled)
    # Then MSG_AREA_LINES + HINT_AREA_LINES + 1 (prompt) at the bottom.
    bottom_reserved: int = MSG_AREA_LINES + HINT_AREA_LINES + 1
    extra_label_row: int = 1 if relabelled else 0
    base_y: int = curses.LINES - 1 - bottom_reserved - 1 - extra_label_row - 1

    def cx(i: int) -> int:
        """Return the screen x of peg ``i``'s centre column."""
        return start_x + presenter.peg_center_x(n, i)

    # Vertical pegs
    with stdscr_attr(stdscr, color_pair(PAIR_DEFAULT)):
        p_idx: int
        for p_idx in range(3):
            i: int
            for i in range(n + 1):
                stdscr.addstr(base_y - i, cx(p_idx), "|")

    # Discs
    pvw: int = presenter.peg_visual_width(n)
    peg: list[int]
    for p_idx, peg in enumerate(session.game.towers):
        size: int
        for i, size in enumerate(peg):
            disc_str: str = "*" * presenter.disk_char_width(size)
            x: int = cx(p_idx) - pvw // 2 + presenter.padding_left(n, size)
            with stdscr_attr(stdscr, color_pair(PAIR_DISC)):
                stdscr.addstr(base_y - i, x, disc_str)

    # Base line
    with stdscr_attr(stdscr, color_pair(PAIR_DEFAULT)):
        stdscr.addstr(base_y + 1, start_x, "=" * presenter.total_width(n))

    # Active labels (coloured by current label per peg)
    for i in range(3):
        with stdscr_attr(stdscr, color_pair(peg_color(labelling, i))):
            stdscr.addstr(
                base_y + 2,
                cx(i),
                str(change_labels_on_pegs(labelling, i) + 1),
            )

    # Default-reference row when relabelled
    if relabelled:
        for i in range(3):
            with stdscr_attr(
                stdscr, color_pair(peg_color(Labelling.ONE_TWO_THREE, i))
            ):
                stdscr.addstr(base_y + 3, cx(i), str(i + 1))


def _draw_top_status(stdscr: curses.window, session: GameSession) -> None:
    """Draw a one-line status at row 0.

    Shows the disc count, the current labelling, the move count and the number
    of saved recipes.

    Args:
        stdscr: The curses window to draw on.
        session: The live game session supplying the status values.
    """
    # a, b, c: the three active peg labels (1-indexed).
    a: int
    b: int
    c: int
    a, b, c = (
        change_labels_on_pegs(session.labelling, i) + 1 for i in range(3)
    )
    text: str = (
        f" Discs: {session.num_disks}    "
        f"Labelling: {a} {b} {c}    "
        f"Moves: {session.current_moves}    "
        f"Recipes: {len(session.registry)} "
    )
    stdscr.move(0, 0)
    stdscr.clrtoeol()
    with stdscr_attr(stdscr, color_pair(PAIR_MESSAGE)):
        stdscr.addstr(0, 0, text[: curses.COLS - 1])


def _draw_messages(stdscr: curses.window, lines: Sequence[str]) -> None:
    """Display up to ``MSG_AREA_LINES`` of message text above the hint area.

    Long outputs are truncated to their last lines.

    Args:
        stdscr: The curses window to draw on.
        lines: The message lines; only the final ``MSG_AREA_LINES`` are shown.
    """
    visible: Sequence[str] = lines[-MSG_AREA_LINES:]
    # Sit above the hint area + prompt: one row for the prompt, plus
    # HINT_AREA_LINES for the hint, then MSG_AREA_LINES going up.
    msg_top: int = curses.LINES - 1 - HINT_AREA_LINES - MSG_AREA_LINES
    i: int
    for i in range(MSG_AREA_LINES):
        stdscr.move(msg_top + i, 0)
        stdscr.clrtoeol()
    line: str
    for i, line in enumerate(visible):
        with stdscr_attr(stdscr, color_pair(PAIR_MESSAGE)):
            stdscr.addstr(msg_top + i, 0, line[: curses.COLS - 1])


def _show_pager(stdscr: curses.window, lines: Sequence[str]) -> None:
    """Full-screen scrollable view for output taller than the message area.

    Used for output that would otherwise be truncated (e.g. the ~11-line
    recipe rebinding table against the 6-line message area). Up/Down or j/k
    scroll a line; PgUp/PgDn or space a page; Home/End jump; q or Enter closes
    and returns to the board.

    Args:
        stdscr: The curses window to draw on.
        lines: The full set of lines to page through.
    """
    body: list[str] = list(lines)
    footer: str = "[Up/Down PgUp/PgDn Home/End scroll - q or Enter to close]"
    top: int = 0
    while True:
        stdscr.erase()
        # keep the last row for the footer
        view_h: int = max(1, curses.LINES - 1)
        maxtop: int = max(0, len(body) - view_h)
        top = max(0, min(top, maxtop))
        i: int
        for i in range(min(view_h, len(body) - top)):
            stdscr.addstr(i, 0, body[top + i][: curses.COLS - 1])
        stdscr.addstr(curses.LINES - 1, 0, footer[: curses.COLS - 1])
        stdscr.refresh()
        key: int = stdscr.getch()
        if key in (ord("q"), ord("Q"), 10, 13, curses.KEY_ENTER):
            return
        if key in (curses.KEY_DOWN, ord("j")):
            top += 1
        elif key in (curses.KEY_UP, ord("k")):
            top -= 1
        elif key in (curses.KEY_NPAGE, ord(" ")):
            top += view_h
        elif key == curses.KEY_PPAGE:
            top -= view_h
        elif key == curses.KEY_HOME:
            top = 0
        elif key == curses.KEY_END:
            top = maxtop


def _draw_hint(
    stdscr: curses.window, hint_lines: Sequence[str] | None = None
) -> None:
    """Draw ``HINT_AREA_LINES`` rows of hint text just above the prompt.

    Shorter inputs are top-padded with empty lines so single-line hints sit
    right above the prompt rather than floating.

    Args:
        stdscr: The curses window to draw on.
        hint_lines: The hint text; defaults to ``DEFAULT_HINT`` when ``None``.
    """
    if hint_lines is None:
        hint_lines = DEFAULT_HINT
    # Pad with empty lines at the top so single-line hints (post-win
    # prompts) sit right above the prompt rather than floating.
    padded: list[str] = [""] * (HINT_AREA_LINES - len(hint_lines)) + list(
        hint_lines
    )
    padded = padded[-HINT_AREA_LINES:]
    top: int = curses.LINES - 1 - HINT_AREA_LINES
    i: int
    for i in range(HINT_AREA_LINES):
        y: int = top + i
        stdscr.move(y, 0)
        stdscr.clrtoeol()
        with stdscr_attr(stdscr, color_pair(PAIR_DEFAULT)):
            stdscr.addstr(y, 0, padded[i][: curses.COLS - 1])


def _redraw(
    stdscr: curses.window,
    session: GameSession,
    msg_lines: Sequence[str],
    hint: Sequence[str] | None = None,
) -> None:
    """Clear and repaint the whole screen: status, board, messages, hint.

    Args:
        stdscr: The curses window to draw on.
        session: The live game session supplying board and status state.
        msg_lines: The message lines to show above the hint area.
        hint: The hint text; defaults to ``DEFAULT_HINT`` when ``None``.
    """
    stdscr.clear()
    _draw_top_status(stdscr, session)
    _draw_board(stdscr, session)
    _draw_messages(stdscr, msg_lines)
    _draw_hint(stdscr, hint)
    stdscr.refresh()


# --- Input ---------------------------------------------------------------


def _read_line(stdscr: curses.window, prompt: str = "> ") -> str | None:
    """Read one line of input at the bottom row.

    Echoes printable characters, handles backspace, ignores resize events,
    and returns on Enter.

    Args:
        stdscr: The curses window to read from and echo onto.
        prompt: The prompt string drawn before the input.

    Returns:
        The typed string, or ``None`` on Ctrl-C / EOF.
    """
    y: int = curses.LINES - 1
    stdscr.move(y, 0)
    stdscr.clrtoeol()
    stdscr.addstr(y, 0, prompt)
    stdscr.refresh()

    buf: list[str] = []
    curs_set(1)
    try:
        while True:
            try:
                ch: int = stdscr.getch()
            except KeyboardInterrupt:
                return None
            if ch == curses.KEY_RESIZE:
                # Caller will handle redraw on the next loop.
                continue
            if ch in (10, 13, curses.KEY_ENTER):
                return "".join(buf)
            if ch in (curses.KEY_BACKSPACE, 127, 8):
                if buf:
                    buf.pop()
                    cy: int
                    cx: int
                    cy, cx = stdscr.getyx()
                    if cx > len(prompt):
                        stdscr.move(cy, cx - 1)
                        stdscr.delch()
                        stdscr.refresh()
                continue
            if 32 <= ch < 127:
                buf.append(chr(ch))
                stdscr.addch(ch)
                stdscr.refresh()
    finally:
        curs_set(0)


# --- Top-level flow ------------------------------------------------------


def _setup_colours() -> None:
    """Initialise the curses colour pairs used by the board, if supported."""
    if has_colors():
        start_color()
        init_pair(PAIR_DISC, COLOR_CYAN, COLOR_BLACK)
        init_pair(PAIR_DEFAULT, COLOR_WHITE, COLOR_BLACK)
        init_pair(PAIR_MESSAGE, COLOR_YELLOW, COLOR_BLACK)
        init_pair(PAIR_ERROR, COLOR_RED, COLOR_BLACK)
        init_pair(PAIR_BLUE, COLOR_BLUE, COLOR_BLACK)


def _prompt_disc_count(stdscr: curses.window) -> int | None:
    """Modally ask for a disc count on a clean screen.

    Re-prompts until a valid count is entered.

    Args:
        stdscr: The curses window to draw the prompt on.

    Returns:
        The chosen disc count in ``1..MAX_DISKS``, or ``None`` to quit.
    """
    while True:
        stdscr.clear()
        with stdscr_attr(stdscr, color_pair(PAIR_MESSAGE)):
            stdscr.addstr(1, 2, "Towers of Hanoi — type 'help' for commands.")
        with stdscr_attr(stdscr, color_pair(PAIR_DEFAULT)):
            stdscr.addstr(3, 2, f"How many discs? (1-{MAX_DISKS}, or 'quit')")
        stdscr.refresh()
        line: str | None = _read_line(stdscr, prompt="> ")
        if line is None:
            return None
        s: str = line.strip().lower()
        if s in ("quit", "q", "exit"):
            return None
        if s.isdigit():
            n: int = int(s)
            if 1 <= n <= MAX_DISKS:
                return n
        # invalid — loop and re-prompt


def _play_game(stdscr: curses.window, n: int, registry: RecipeRegistry) -> bool:
    """Play one game to a win or exit inside the curses UI.

    Args:
        stdscr: The curses window to draw on and read from.
        n: The number of discs to start with.
        registry: The recipe store shared across games.

    Returns:
        ``True`` if the user wants to play again, ``False`` to exit.
    """
    if not _check_size(stdscr, n):
        _show_too_small(stdscr, n)
        if not _check_size(stdscr, n):
            return False

    session: GameSession = GameSession(num_disks=n, registry=registry)
    msg_lines: list[str] = []

    while not session.is_won():
        _redraw(stdscr, session, msg_lines)
        text: str | None = _read_line(stdscr)
        if text is None:
            return False
        cmd: Command = parse(text)
        result: DispatchResult = session.dispatch(cmd)
        if result.quit:
            return False
        # A plain move under a relabelling gets the same three-column rebinding
        # table `apply` shows (empty otherwise — see move_teaching_lines).
        show_lines: list[str] = list(
            result.lines
        ) + session.move_teaching_lines(cmd, result)
        if len(show_lines) > MSG_AREA_LINES:
            # Taller than the message area (e.g. the apply table) — page it in a
            # scrollable overlay instead of truncating, then clear the area.
            _show_pager(stdscr, show_lines)
            msg_lines = []
        else:
            msg_lines = show_lines

    # Won
    min_moves: int = session.min_moves()
    banner: list[str] = [
        f"Solved! {session.current_moves} moves (minimum {min_moves})."
    ]
    if session.current_moves == min_moves:
        banner.append("Optimal solution!")
    else:
        extra: int = session.current_moves - min_moves
        banner.append(f"{extra} more than the minimum.")
    _redraw(
        stdscr,
        session,
        banner,
        hint=["Save this solution? Type a name, or press Enter to skip."],
    )
    name: str | None = _read_line(stdscr)
    if name and name.strip():
        msg: str = session.save_recipe(name.strip())
        _redraw(
            stdscr,
            session,
            banner + [msg],
            hint=["Play again? (y/n)"],
        )
    else:
        _redraw(stdscr, session, banner, hint=["Play again? (y/n)"])
    again: str | None = _read_line(stdscr)
    if again is None:
        return False
    return again.strip().lower().startswith("y")


def _main(stdscr: curses.window) -> None:
    """Curses-wrapped main loop: set up, then play games until the user quits.

    Args:
        stdscr: The root window supplied by ``curses.wrapper``.
    """
    _setup_colours()
    curs_set(0)
    stdscr.keypad(True)

    registry: RecipeRegistry = RecipeRegistry()
    while True:
        n: int | None = _prompt_disc_count(stdscr)
        if n is None:
            return
        if not _play_game(stdscr, n, registry):
            return


def main() -> None:
    """Console-script entry point: run the curses UI via ``curses.wrapper``."""
    curses.wrapper(_main)


if __name__ == "__main__":
    main()
