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
from typing import List, Optional

from . import presenter
from .commands import parse
from .engine import GameSession
from .presenter import Labelling, change_labels_on_pegs, peg_color
from .recipe import RecipeRegistry

MAX_DISKS = 10
MSG_AREA_LINES = 6  # max message lines shown between board and hint
HINT_AREA_LINES = 2  # rows reserved for hint text above the prompt

# Default hint shown during play. The first line spells out the move
# syntax explicitly so a brand-new user knows what to type without having
# to discover the 'help' command first.
DEFAULT_HINT = [
    "Move: type 'from -> to' (e.g. '1 -> 3')",
    "Other: relabel a b c | apply <name> | show <name> | list | help | quit",
]

# Curses colour-pair numbers
PAIR_DISC = 1
PAIR_DEFAULT = 2
PAIR_MESSAGE = 3
PAIR_ERROR = 4
PAIR_BLUE = 5  # also used by presenter.peg_color


@contextmanager
def stdscr_attr(stdscr, attr):
    stdscr.attron(attr)
    try:
        yield
    finally:
        stdscr.attroff(attr)


# --- Drawing primitives ---------------------------------------------------


def _required_rows(num_disks: int) -> int:
    """Minimum LINES needed: board (n+4 worst-case) + 1 gap + msg area +
    hint area + prompt."""
    return (num_disks + 4) + 1 + MSG_AREA_LINES + HINT_AREA_LINES + 1


def _required_cols(num_disks: int) -> int:
    return presenter.total_width(num_disks) + 4


def _check_size(stdscr, num_disks: int) -> bool:
    return curses.LINES >= _required_rows(
        num_disks
    ) and curses.COLS >= _required_cols(num_disks)


def _show_too_small(stdscr, num_disks: int) -> None:
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


def _draw_board(stdscr, session: GameSession) -> None:
    """Draw the board centred horizontally with the bottom of the base
    above the message area."""
    n = session.num_disks
    labelling = session.labelling
    relabelled = labelling != Labelling.ONE_TWO_THREE

    start_x = max(0, (curses.COLS - presenter.total_width(n)) // 2)
    # base_y is the bottom row of disc slots. Below that:
    #   base_y + 1: base line
    #   base_y + 2: active label row
    #   base_y + 3: default reference row (only when relabelled)
    # Then MSG_AREA_LINES + HINT_AREA_LINES + 1 (prompt) at the bottom.
    bottom_reserved = MSG_AREA_LINES + HINT_AREA_LINES + 1
    extra_label_row = 1 if relabelled else 0
    base_y = curses.LINES - 1 - bottom_reserved - 1 - extra_label_row - 1

    def cx(i: int) -> int:
        return start_x + presenter.peg_center_x(n, i)

    # Vertical pegs
    with stdscr_attr(stdscr, color_pair(PAIR_DEFAULT)):
        for p_idx in range(3):
            for i in range(n + 1):
                stdscr.addstr(base_y - i, cx(p_idx), "|")

    # Discs
    pvw = presenter.peg_visual_width(n)
    for p_idx, peg in enumerate(session.game.towers):
        for i, size in enumerate(peg):
            disc_str = "*" * presenter.disk_char_width(size)
            x = cx(p_idx) - pvw // 2 + presenter.padding_left(n, size)
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


def _draw_top_status(stdscr, session: GameSession) -> None:
    """One-line status at row 0: disc count, current labelling, move count."""
    a, b, c = (
        change_labels_on_pegs(session.labelling, i) + 1 for i in range(3)
    )
    text = (
        f" Discs: {session.num_disks}    "
        f"Labelling: {a} {b} {c}    "
        f"Moves: {session.current_moves}    "
        f"Recipes: {len(session.registry)} "
    )
    stdscr.move(0, 0)
    stdscr.clrtoeol()
    with stdscr_attr(stdscr, color_pair(PAIR_MESSAGE)):
        stdscr.addstr(0, 0, text[: curses.COLS - 1])


def _draw_messages(stdscr, lines: List[str]) -> None:
    """Display up to MSG_AREA_LINES of message text just above the hint
    area. Long outputs are truncated to the last lines."""
    visible = lines[-MSG_AREA_LINES:]
    # Sit above the hint area + prompt: one row for the prompt, plus
    # HINT_AREA_LINES for the hint, then MSG_AREA_LINES going up.
    msg_top = curses.LINES - 1 - HINT_AREA_LINES - MSG_AREA_LINES
    for i in range(MSG_AREA_LINES):
        stdscr.move(msg_top + i, 0)
        stdscr.clrtoeol()
    for i, line in enumerate(visible):
        with stdscr_attr(stdscr, color_pair(PAIR_MESSAGE)):
            stdscr.addstr(msg_top + i, 0, line[: curses.COLS - 1])


def _draw_hint(stdscr, hint_lines: Optional[List[str]] = None) -> None:
    """Draw HINT_AREA_LINES rows of hint text just above the prompt.
    Shorter inputs are top-padded with empty lines."""
    if hint_lines is None:
        hint_lines = DEFAULT_HINT
    # Pad with empty lines at the top so single-line hints (post-win
    # prompts) sit right above the prompt rather than floating.
    padded = [""] * (HINT_AREA_LINES - len(hint_lines)) + list(hint_lines)
    padded = padded[-HINT_AREA_LINES:]
    top = curses.LINES - 1 - HINT_AREA_LINES
    for i in range(HINT_AREA_LINES):
        y = top + i
        stdscr.move(y, 0)
        stdscr.clrtoeol()
        with stdscr_attr(stdscr, color_pair(PAIR_DEFAULT)):
            stdscr.addstr(y, 0, padded[i][: curses.COLS - 1])


def _redraw(
    stdscr,
    session: GameSession,
    msg_lines: List[str],
    hint: Optional[List[str]] = None,
) -> None:
    stdscr.clear()
    _draw_top_status(stdscr, session)
    _draw_board(stdscr, session)
    _draw_messages(stdscr, msg_lines)
    _draw_hint(stdscr, hint)
    stdscr.refresh()


# --- Input ---------------------------------------------------------------


def _read_line(stdscr, prompt: str = "> ") -> Optional[str]:
    """Read one line of input at the bottom row. Returns the typed string,
    or None if Ctrl-C / EOF."""
    y = curses.LINES - 1
    stdscr.move(y, 0)
    stdscr.clrtoeol()
    stdscr.addstr(y, 0, prompt)
    stdscr.refresh()

    buf: List[str] = []
    curs_set(1)
    try:
        while True:
            try:
                ch = stdscr.getch()
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
    if has_colors():
        start_color()
        init_pair(PAIR_DISC, COLOR_CYAN, COLOR_BLACK)
        init_pair(PAIR_DEFAULT, COLOR_WHITE, COLOR_BLACK)
        init_pair(PAIR_MESSAGE, COLOR_YELLOW, COLOR_BLACK)
        init_pair(PAIR_ERROR, COLOR_RED, COLOR_BLACK)
        init_pair(PAIR_BLUE, COLOR_BLUE, COLOR_BLACK)


def _prompt_disc_count(stdscr) -> Optional[int]:
    """Modal: ask for disc count on a clean screen. None = quit."""
    while True:
        stdscr.clear()
        with stdscr_attr(stdscr, color_pair(PAIR_MESSAGE)):
            stdscr.addstr(1, 2, "Towers of Hanoi — type 'help' for commands.")
        with stdscr_attr(stdscr, color_pair(PAIR_DEFAULT)):
            stdscr.addstr(3, 2, f"How many discs? (1-{MAX_DISKS}, or 'quit')")
        stdscr.refresh()
        line = _read_line(stdscr, prompt="> ")
        if line is None:
            return None
        s = line.strip().lower()
        if s in ("quit", "q", "exit"):
            return None
        if s.isdigit():
            n = int(s)
            if 1 <= n <= MAX_DISKS:
                return n
        # invalid — loop and re-prompt


def _play_game(stdscr, n: int, registry: RecipeRegistry) -> bool:
    """Returns True if the user wants to play again, False to exit."""
    if not _check_size(stdscr, n):
        _show_too_small(stdscr, n)
        if not _check_size(stdscr, n):
            return False

    session = GameSession(num_disks=n, registry=registry)
    msg_lines: List[str] = []

    while not session.is_won():
        _redraw(stdscr, session, msg_lines)
        text = _read_line(stdscr)
        if text is None:
            return False
        result = session.dispatch(parse(text))
        if result.quit:
            return False
        if result.lines:
            msg_lines = result.lines
        else:
            msg_lines = []

    # Won
    min_moves = session.min_moves()
    banner = [f"Solved! {session.current_moves} moves (minimum {min_moves})."]
    if session.current_moves == min_moves:
        banner.append("Optimal solution!")
    else:
        extra = session.current_moves - min_moves
        banner.append(f"{extra} more than the minimum.")
    _redraw(
        stdscr,
        session,
        banner,
        hint=["Save this solution? Type a name, or press Enter to skip."],
    )
    name = _read_line(stdscr)
    if name and name.strip():
        msg = session.save_recipe(name.strip())
        _redraw(
            stdscr,
            session,
            banner + [msg],
            hint=["Play again? (y/n)"],
        )
    else:
        _redraw(stdscr, session, banner, hint=["Play again? (y/n)"])
    again = _read_line(stdscr)
    if again is None:
        return False
    return again.strip().lower().startswith("y")


def _main(stdscr) -> None:
    _setup_colours()
    curs_set(0)
    stdscr.keypad(True)

    registry = RecipeRegistry()
    while True:
        n = _prompt_disc_count(stdscr)
        if n is None:
            return
        if not _play_game(stdscr, n, registry):
            return


def main() -> None:
    curses.wrapper(_main)


if __name__ == "__main__":
    main()
