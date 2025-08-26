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
from enum import Enum, auto
from typing import Callable, List

from _curses import window
from hanoimodel import HanoiGame

show_disks = True


class Labelling(Enum):
    ONE_TWO_THREE = auto()
    ONE_THREE_TWO = auto()
    TWO_ONE_THREE = auto()


# --- Helper Classes ---

labelling = Labelling.ONE_TWO_THREE


def change_labels_on_pegs(tower_index):
    if labelling == Labelling.ONE_TWO_THREE:
        return [0, 1, 2][tower_index]
    if labelling == Labelling.ONE_THREE_TWO:
        return [0, 2, 1][tower_index]
    if labelling == Labelling.TWO_ONE_THREE:
        return [1, 0, 2][tower_index]


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

    if (
        curses.COLS < hanoi_game.min_cols()
        or curses.LINES < hanoi_game.min_rows()
    ):
        stdscr.addstr(
            0,
            0,
            f"Terminal too small! Min {hanoi_game.min_cols()} cols, {hanoi_game.min_rows()} rows needed.",
        )
        stdscr.addstr(
            1,
            0,
            f"Current: {curses.COLS} cols, {curses.LINES} rows. Resize and restart.",
        )
        stdscr.refresh()
        while (
            curses.COLS < hanoi_game.min_cols()
            or curses.LINES < hanoi_game.min_rows()
        ):
            time.sleep(0.1)
            stdscr.clear()
            stdscr.addstr(
                0,
                0,
                f"Terminal too small! Min {hanoi_game.min_cols()} cols, {hanoi_game.min_rows()} rows needed.",
            )
            stdscr.addstr(
                1,
                0,
                f"Current: {curses.COLS} cols, {curses.LINES} rows. Resize and restart.",
            )
            stdscr.refresh()
        stdscr.clear()
    start_x: int = (curses.COLS - hanoi_game.total_game_content_width()) // 2
    if start_x < 0:
        start_x = 0
    base_y: int = curses.LINES - 3  # Position for the base of the pegs

    # Draw peg labels

    def peg_center_x(i) -> int:
        return (
            start_x
            + i * (hanoi_game.peg_visual_width() + hanoi_game.peg_gap())
            + hanoi_game.peg_visual_width() // 2
        )

    with stdscr_attr(stdscr, color_pair(2)):
        for i in range(3):
            stdscr.addstr(
                base_y + 2, peg_center_x(i), f"{change_labels_on_pegs(i) + 1}"
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
            if show_disks:
                draw_disk(
                    game=hanoi_game,
                    stdscr=stdscr,
                    y=base_y - i,
                    x=peg_center_x(p_idx),
                    size=peg[i],
                    max_disk_size=hanoi_game.max_disk_size(),
                )

    # Draw base line
    with stdscr_attr(stdscr, color_pair(2)):
        base_str = "=" * hanoi_game.total_game_content_width()
        stdscr.addstr(base_y + 1, start_x, base_str)

    # Display moves
    with stdscr_attr(stdscr, color_pair(3)):
        stdscr.addstr(curses.LINES - 1, 0, f"Moves: {hanoi_game.current_moves}")
    stdscr.refresh()


# --- Display Functions (Curses Specific) ---
def draw_disk(
    game: HanoiGame,
    stdscr: window,
    y: int,
    x: int,
    size: int,
    max_disk_size: int,
):
    """Draws a single disk at the given coordinates."""
    if size == 0:
        return
    with stdscr_attr(stdscr, color_pair(1)):
        disk_str: str = "*" * game.disk_char_width(size)
        stdscr.addstr(
            y,
            x - (game.peg_visual_width() // 2) + game.padding_left(size),
            disk_str,
        )


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
            msg="Use UP/DOWN arrows, then ENTER to select. Press Q to quit",
            row=0,
        )  # Status message
        display_message(
            stdscr=stdscr,
            msg="Press M to toggle showing discs",
            row=1,
        )  # Status message
        display_message(
            stdscr=stdscr,
            msg="Press 1 2 or 3 to change labels",
            row=2,
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
        elif key == ord("m") or key == ord("M"):

            def toggle_show_discs():
                global show_disks
                show_disks = not show_disks

            return MenuButton(
                id="toggle", text="", x=0, y=0, action=toggle_show_discs
            )
        elif key == ord("1"):

            def set_labelling():
                global labelling
                labelling = Labelling.ONE_TWO_THREE

            return MenuButton(
                id="one_two_three", text="", x=0, y=0, action=set_labelling
            )
        elif key == ord("2"):

            def set_labelling():
                global labelling
                labelling = Labelling.ONE_THREE_TWO

            return MenuButton(
                id="one_two_three", text="", x=0, y=0, action=set_labelling
            )
        elif key == ord("3"):

            def set_labelling():
                global labelling
                labelling = Labelling.TWO_ONE_THREE

            return MenuButton(
                id="one_two_three", text="", x=0, y=0, action=set_labelling
            )

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

    # Position buttons centrally

    def select_number_of_disks() -> int:
        stdscr.clear()

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
        if selected_disk.id == "toggle":
            selected_disk.action()
        if selected_disk.id == "one two three":
            selected_disk.action()
        return selected_disk.action()

    def run_game_loop(number_of_disks) -> HanoiGame:
        game: HanoiGame = HanoiGame(num_disks=number_of_disks)
        global labelling
        labelling = Labelling.ONE_TWO_THREE
        # --- Game Loop ---
        while not game.check_win_condition():
            draw_game_state(game, stdscr)  # Draw the game board first
            # Generate valid move buttons dynamically
            move_buttons: List = []

            # for (from_p, to_p), action in game.move_options():
            for valid_move in game.move_options():
                move_buttons.append(
                    MenuButton(
                        id=(valid_move.move.from_peg, valid_move.move.to_peg),
                        text=f"{change_labels_on_pegs(valid_move.move.from_peg) + 1} -> {change_labels_on_pegs(valid_move.move.to_peg) + 1}",
                        x=0,
                        y=0,
                        action=valid_move.action,
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

            move_menu_start_y = (
                curses.LINES - 1 + 2
            )  # Two lines below move count
            if move_menu_start_y + len(move_buttons) >= curses.LINES:
                move_menu_start_y = 4
            max_move_text_width: int = max(
                len(btn.text) for btn in move_buttons
            )
            move_menu_start_x: int = (curses.COLS // 2) - (
                max_move_text_width // 2
            )
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
        return game

    def game_over(game):
        global show_disks
        show_disks = True

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
                    stdscr=stdscr,
                    msg="You achieved the optimal solution!",
                    row=2,
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
            stdscr=stdscr,
            msg="Press any key to go to the main screen...",
            row=curses.LINES - 1,
        )
        stdscr.getch()

    while True:
        game_over(run_game_loop(select_number_of_disks()))


if __name__ == "__main__":
    curses.wrapper(main)
