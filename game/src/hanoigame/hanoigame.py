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

import curses
import sys
import time
from contextlib import contextmanager
from curses import (
    A_REVERSE,
    COLOR_BLACK,
    COLOR_CYAN,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    KEY_DOWN,
    KEY_ENTER,
    KEY_UP,
    color_pair,
    curs_set,
    has_colors,
    init_pair,
    start_color,
)
from dataclasses import dataclass
from typing import Callable, List

from _curses import window
from hanoimodel import HanoiGame

# --- Helper Classes ---


@dataclass
class MenuButton:
    """Represents a button in a curses menu."""

    id: any
    text: str
    x: int
    y: int
    action: Callable

    def __post_init__(self):
        if not self.action:
            self.action = lambda: id


@contextmanager
def stdscr_attr(stdscr: window, x: int):
    stdscr.attron(x)
    try:
        yield
    finally:
        stdscr.attroff(x)


def draw_game_state(hanoi_game: HanoiGame, stdscr: window):
    """Clears the screen and draws the current state of the game."""
    stdscr.clear()
    max_disk_size: int = hanoi_game.num_disks
    peg_visual_width: int = max_disk_size * 2 - 1
    peg_gap: int = 5
    total_game_content_width: int = (peg_visual_width + peg_gap) * 3 - peg_gap
    min_cols: int = total_game_content_width + 4  # A little padding
    min_rows: int = (
        hanoi_game.num_disks + 6
    )  # Enough space for disks, base, messages

    if curses.COLS < min_cols or curses.LINES < min_rows:
        stdscr.addstr(
            0,
            0,
            f"Terminal too small! Min {min_cols} cols, {min_rows} rows needed.",
        )
        stdscr.addstr(
            1,
            0,
            f"Current: {curses.COLS} cols, {curses.LINES} rows. Resize and restart.",
        )
        stdscr.refresh()
        while curses.COLS < min_cols or curses.LINES < min_rows:
            time.sleep(0.1)
            stdscr.clear()
            stdscr.addstr(
                0,
                0,
                f"Terminal too small! Min {min_cols} cols, {min_rows} rows needed.",
            )
            stdscr.addstr(
                1,
                0,
                f"Current: {curses.COLS} cols, {curses.LINES} rows. Resize and restart.",
            )
            stdscr.refresh()
        stdscr.clear()
    start_x: int = (curses.COLS - total_game_content_width) // 2
    if start_x < 0:
        start_x = 0
    base_y: int = curses.LINES - 3  # Position for the base of the pegs

    # Draw peg labels

    def peg_center_x(i) -> int:
        return (
            start_x + i * (peg_visual_width + peg_gap) + peg_visual_width // 2
        )

    with stdscr_attr(stdscr, color_pair(2)):
        for i in range(3):
            stdscr.addstr(
                base_y + 2, peg_center_x(i), f"{i + 1}"
            )  # 1-indexed for user

    # Draw the pegs (vertical lines)
    with stdscr_attr(stdscr, color_pair(2)):
        for p_idx in range(3):
            for i in range(
                hanoi_game.num_disks + 1
            ):  # +1 for the top of the peg
                stdscr.addstr(base_y - i, peg_center_x(p_idx), "|")

    # Draw disks - CORRECTION HERE: Iterate from bottom (index 0) to top of stack
    for p_idx, peg in enumerate(hanoi_game.towers):
        for i in range(len(peg)):  # Iterate from bottom (index 0) to top
            # y-coordinate: base_y (bottom) - i (offset for disk's height)
            draw_disk(
                stdscr=stdscr,
                y=base_y - i,
                x=peg_center_x(p_idx),
                size=peg[i],
                max_disk_size=max_disk_size,
            )

    # Draw base line
    with stdscr_attr(stdscr, color_pair(2)):
        base_str = "=" * total_game_content_width
        stdscr.addstr(base_y + 1, start_x, base_str)

    # Display moves
    with stdscr_attr(stdscr, color_pair(3)):
        stdscr.addstr(curses.LINES - 1, 0, f"Moves: {hanoi_game.current_moves}")
    stdscr.refresh()


# --- Display Functions (Curses Specific) ---
def draw_disk(stdscr: window, y: int, x: int, size: int, max_disk_size: int):
    """Draws a single disk at the given coordinates."""
    if size == 0:
        return
    disk_char_width: int = size * 2 - 1
    peg_visual_width: int = max_disk_size * 2 - 1
    padding_left: int = (peg_visual_width - disk_char_width) // 2
    with stdscr_attr(stdscr, color_pair(1)):
        disk_str: str = "*" * disk_char_width
        stdscr.addstr(y, x - (peg_visual_width // 2) + padding_left, disk_str)


def display_message(stdscr: window, msg: str, row: int = 0):
    """Displays a message at a specific row, clearing the line first."""
    stdscr.move(row, 0)
    stdscr.clrtoeol()
    with stdscr_attr(stdscr, color_pair(3)):
        stdscr.addstr(row, 0, msg)
    stdscr.refresh()


def display_menu(
    stdscr: window, buttons: List[MenuButton], current_selection: int
):
    """Draws a list of buttons, highlighting the selected one."""

    for i, button in enumerate(buttons):
        with stdscr_attr(
            stdscr,
            (A_REVERSE | color_pair(3))
            if (i == current_selection)
            else color_pair(2),
        ):
            # Clear the line before drawing button text to ensure no artifacts from previous highlights
            stdscr.move(button.y, button.x)
            stdscr.clrtoeol()
            stdscr.addstr(button.y, button.x, button.text)
    stdscr.refresh()


def get_button_choice(stdscr: window, buttons: List[MenuButton]) -> MenuButton:
    """Allows user to navigate and select a button using arrow keys and Enter."""
    current_selection: int = 0
    # Ensure button positions are set correctly before initial display
    # (This is handled by the calling function before calling get_button_choice)
    while True:
        # We don't clear() here as draw_game_state() is responsible for that in the game loop
        # and we want the menu to appear on top of the game board.
        # Display buttons
        display_menu(stdscr, buttons, current_selection)
        display_message(
            stdscr=stdscr,
            msg="Use UP/DOWN arrows, then ENTER to select. Press Q to quit.",
            row=0,
        )  # Status message
        key: int = stdscr.getch()
        if key == KEY_UP:
            current_selection = (current_selection - 1 + len(buttons)) % len(
                buttons
            )
        elif key == KEY_DOWN:
            current_selection = (current_selection + 1) % len(buttons)
        elif key == KEY_ENTER or key == 10:  # Enter key
            return buttons[current_selection]
        elif key == ord("q") or key == ord("Q"):  # Allow 'Q' to quit from menus
            return MenuButton(
                id="quit", text="", x=0, y=0, action=lambda: sys.exit(0)
            )


# --- Main Game Loop (wrapped for safety) ---
def main(stdscr: window):
    if has_colors():
        start_color()
        # init pair(pair_number, fg, bg)
        init_pair(1, COLOR_CYAN, COLOR_BLACK)  # Disks
        init_pair(2, COLOR_WHITE, COLOR_BLACK)  # Pegs/Base
        init_pair(3, COLOR_YELLOW, COLOR_BLACK)  # Messages/Highlight
        init_pair(4, COLOR_RED, COLOR_BLACK)  # Error messages
    curs_set(0)  # Hide cursor by default
    # --- Disk Selection Menu ---
    disk_buttons: List[MenuButton] = [
        MenuButton(id=1, text="1 Disks", x=0, y=0, action=lambda: 1),
        MenuButton(id=2, text="2 Disks", x=0, y=0, action=lambda: 2),
        MenuButton(id=3, text="3 Disks", x=0, y=0, action=lambda: 3),
        MenuButton(id=4, text="4 Disks", x=0, y=0, action=lambda: 4),
        MenuButton(id=5, text="5 Disks", x=0, y=0, action=lambda: 5),
        MenuButton(id=6, text="6 Disks", x=0, y=0, action=lambda: 6),
        MenuButton(id=7, text="7 Disks", x=0, y=0, action=lambda: 7),
        MenuButton(id=8, text="8 Disks", x=0, y=0, action=lambda: 8),
        MenuButton(id=9, text="9 Disks", x=0, y=0, action=lambda: 9),
        MenuButton(id=10, text="10 Disks", x=0, y=0, action=lambda: 10),
    ]
    # Position buttons centrally
    stdscr.clear()

    def prompt_select_number_of_disks() -> None:
        menu_start_y: int = (curses.LINES // 2) - (len(disk_buttons) // 2)
        max_text_width: int = max(len(btn.text) for btn in disk_buttons)
        menu_start_x: int = (curses.COLS // 2) - (max_text_width // 2)
        # Adjust button positions for display_menu
        for i, btn in enumerate(disk_buttons):
            btn.y = menu_start_y + i
            btn.x = menu_start_x
        stdscr.addstr(
            menu_start_y - 2, menu_start_x - 5, "Select Number of Disks:"
        )

    prompt_select_number_of_disks()
    stdscr.refresh()
    selected_disk: MenuButton = get_button_choice(stdscr, disk_buttons)
    if selected_disk.id == "quit":
        selected_disk.action()

    game: HanoiGame = HanoiGame(num_disks=selected_disk.action())
    # --- Game Loop ---
    while not game.check_win_condition():
        draw_game_state(game, stdscr)  # Draw the game board first
        # Generate valid move buttons dynamically
        move_buttons: List = []

        for (from_p, to_p), action in game.valid_moves():
            move_buttons.append(
                MenuButton(
                    id=(from_p, to_p),
                    text=f"{from_p + 1} -> {to_p + 1}",
                    x=0,
                    y=0,
                    action=action,
                )
            )
        if not move_buttons:
            # This should only happen when the game is won, but as a safeguard
            display_message(
                stdstr=stdscr,
                msg="No valid moves available! (Perhaps game is won?)",
                row=1,
            )
            stdscr.getch()  # Wait for user to acknowledge
            continue

        move_menu_start_y = curses.LINES - 1 + 2  # Two lines below move count
        if move_menu_start_y + len(move_buttons) >= curses.LINES:
            move_menu_start_y = 4
        max_move_text_width: int = max(len(btn.text) for btn in move_buttons)
        move_menu_start_x: int = (curses.COLS // 2) - (max_move_text_width // 2)
        # Adjust button positions for get_button_choice
        for i, btn in enumerate(move_buttons):
            btn.y = move_menu_start_y + i
            btn.x = move_menu_start_x
        selected_move_tuple: MenuButton = get_button_choice(
            stdscr, move_buttons
        )
        if selected_move_tuple.id == "quit":
            break
        selected_move_tuple.action()
        time.sleep(0.1)  # Small delay for visual effect of move
    # --- Game Over / Win Message ---
    draw_game_state(game, stdscr)  # Draw final state
    if game.check_win_condition():
        min_moves: int = (2**game.num_disks) - 1
        display_message(
            stdscr=stdscr, msg="Congratulations! You solved it!", row=0
        )
        display_message(
            stdscr=stdscr,
            msg=f"Total Moves: {game.current_moves}. Minimum moves: {min_moves}",
            row=1,
        )
        if game.current_moves == min_moves:
            display_message(
                stdscr=stdscr, msg="You achieved the optimal solution!", row=2
            )
        else:
            display_message(
                stdscr=stdscr,
                msg=f"You took {game.current_moves - min_moves} more moves than the optimum.",
                row=2,
            )
    else:
        display_message(
            stdscr=stdscr, msg="Game ended. Thanks for playing!", row=0
        )
    display_message(
        stdscr=stdscr, msg="Press any key to exit...", row=curses.LINES - 1
    )
    stdscr.getch()


if __name__ == "__main__":
    curses.wrapper(main)
