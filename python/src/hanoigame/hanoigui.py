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

"""wxPython front-end for HanoiGame.

Plain-text board (monospace `wx.TextCtrl`) plus a button-driven control
panel: six move buttons (auto-enabled from `game.move_options()`), six
relabel permutation buttons, and a recipe list with Save / Apply / Show.
Same `engine.GameSession` dispatcher as the CLI and curses, so behaviour
stays consistent across all three frontends.
"""

from typing import Optional, Tuple

import wx

from . import presenter
from .commands import ApplyCmd, MoveCmd, RelabelCmd, ShowCmd
from .engine import GameSession
from .presenter import change_labels_on_pegs
from .recipe import RecipeRegistry

MAX_DISKS = 10
DEFAULT_DISKS = 3

ALL_LABEL_PAIRS: Tuple[Tuple[int, int], ...] = (
    (1, 2),
    (1, 3),
    (2, 1),
    (2, 3),
    (3, 1),
    (3, 2),
)

ALL_RELABEL_PERMUTATIONS: Tuple[Tuple[int, int, int], ...] = (
    (1, 2, 3),
    (1, 3, 2),
    (2, 1, 3),
    (2, 3, 1),
    (3, 1, 2),
    (3, 2, 1),
)


class HanoiFrame(wx.Frame):
    def __init__(self) -> None:
        super().__init__(None, title="Towers of Hanoi", size=(900, 900))
        self.registry = RecipeRegistry()
        self.session: Optional[GameSession] = None
        self.move_buttons: dict = {}
        self.relabel_buttons: dict = {}
        self._build_ui()
        self._new_game(DEFAULT_DISKS)

    # --- UI construction --------------------------------------------------

    def _build_ui(self) -> None:
        self.panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        mono = wx.Font(
            12,
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )

        # Top: disc count chooser + new game. Two explicit ± buttons
        # straddling a count label — clearer than wx.SpinCtrl, whose
        # tiny built-in arrows are easy to misread.
        self.disc_count_value = DEFAULT_DISKS
        top_row = wx.BoxSizer(wx.HORIZONTAL)
        top_row.Add(
            wx.StaticText(self.panel, label="Discs:"),
            flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            border=5,
        )
        dec_btn = wx.Button(self.panel, label="−", size=(40, -1))
        dec_btn.Bind(wx.EVT_BUTTON, lambda _evt: self._adjust_disc_count(-1))
        top_row.Add(dec_btn, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=4)
        self.disc_count_label = wx.StaticText(
            self.panel, label=str(DEFAULT_DISKS)
        )
        self.disc_count_label.SetFont(mono)
        top_row.Add(
            self.disc_count_label,
            flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT,
            border=8,
        )
        inc_btn = wx.Button(self.panel, label="+", size=(40, -1))
        inc_btn.Bind(wx.EVT_BUTTON, lambda _evt: self._adjust_disc_count(1))
        top_row.Add(
            inc_btn, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=10
        )
        new_btn = wx.Button(self.panel, label="New Game")
        new_btn.Bind(wx.EVT_BUTTON, self._on_new_game)
        top_row.Add(new_btn, flag=wx.ALIGN_CENTER_VERTICAL)
        top_row.AddStretchSpacer()
        self.status_label = wx.StaticText(self.panel, label="")
        self.status_label.SetFont(mono)
        top_row.Add(self.status_label, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(top_row, flag=wx.EXPAND | wx.ALL, border=8)

        # Board — the only flexible row in the layout, so it absorbs any
        # extra window height (important when the user picks 10 discs).
        board_box = wx.StaticBoxSizer(wx.VERTICAL, self.panel, "Board")
        self.board = wx.TextCtrl(
            self.panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL,
            size=(-1, 280),
        )
        self.board.SetFont(mono)
        # Re-centre the board contents whenever the panel resizes, so the
        # game stays bottom-centred (matching the curses layout).
        self.board.Bind(wx.EVT_SIZE, self._on_board_resize)
        board_box.Add(
            self.board, proportion=1, flag=wx.EXPAND | wx.ALL, border=4
        )
        sizer.Add(
            board_box,
            proportion=1,
            flag=wx.EXPAND | wx.LEFT | wx.RIGHT,
            border=8,
        )

        # Move buttons (always-visible 1x6 row, enabled per move_options)
        move_box = wx.StaticBoxSizer(wx.HORIZONTAL, self.panel, "Move")
        for from_label, to_label in ALL_LABEL_PAIRS:
            btn = wx.Button(self.panel, label=f"{from_label}  →  {to_label}")
            btn.Bind(
                wx.EVT_BUTTON,
                lambda evt, f=from_label, t=to_label: self._on_move(f, t),
            )
            move_box.Add(btn, proportion=1, flag=wx.EXPAND | wx.ALL, border=2)
            self.move_buttons[(from_label, to_label)] = btn
        sizer.Add(
            move_box, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=8
        )

        # Relabel buttons
        relabel_box = wx.StaticBoxSizer(
            wx.HORIZONTAL, self.panel, "Relabel pegs (physical 1, 2, 3 →)"
        )
        for labels in ALL_RELABEL_PERMUTATIONS:
            text = f"{labels[0]}  {labels[1]}  {labels[2]}"
            btn = wx.Button(self.panel, label=text)
            btn.Bind(
                wx.EVT_BUTTON,
                lambda evt, lab=labels: self._on_relabel(lab),
            )
            relabel_box.Add(
                btn, proportion=1, flag=wx.EXPAND | wx.ALL, border=2
            )
            self.relabel_buttons[labels] = btn
        sizer.Add(
            relabel_box, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=8
        )

        # Recipes
        recipe_box = wx.StaticBoxSizer(wx.VERTICAL, self.panel, "Recipes")
        self.recipe_list = wx.ListBox(self.panel, size=(-1, 110))
        self.recipe_list.SetFont(mono)
        recipe_box.Add(
            self.recipe_list, proportion=1, flag=wx.EXPAND | wx.ALL, border=4
        )
        recipe_btns = wx.BoxSizer(wx.HORIZONTAL)
        self.save_btn = wx.Button(self.panel, label="Save Current Solution")
        self.save_btn.Bind(wx.EVT_BUTTON, self._on_save)
        self.apply_btn = wx.Button(self.panel, label="Apply Selected")
        self.apply_btn.Bind(wx.EVT_BUTTON, self._on_apply)
        self.show_btn = wx.Button(self.panel, label="Show Selected")
        self.show_btn.Bind(wx.EVT_BUTTON, self._on_show)
        for b in (self.save_btn, self.apply_btn, self.show_btn):
            recipe_btns.Add(b, flag=wx.RIGHT, border=6)
        recipe_box.Add(
            recipe_btns, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=4
        )
        sizer.Add(
            recipe_box, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=8
        )

        # Last action / messages
        msg_box = wx.StaticBoxSizer(wx.VERTICAL, self.panel, "Last action")
        self.message = wx.TextCtrl(
            self.panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            size=(-1, 110),
        )
        self.message.SetFont(mono)
        msg_box.Add(
            self.message, proportion=1, flag=wx.EXPAND | wx.ALL, border=4
        )
        sizer.Add(msg_box, flag=wx.EXPAND | wx.ALL, border=8)

        self.panel.SetSizer(sizer)
        self.Center()

    # --- Event handlers --------------------------------------------------

    def _on_new_game(self, _evt) -> None:
        self._new_game(self.disc_count_value)
        self._set_message("New game.")

    def _adjust_disc_count(self, delta: int) -> None:
        new = max(1, min(MAX_DISKS, self.disc_count_value + delta))
        if new == self.disc_count_value:
            return
        self.disc_count_value = new
        self.disc_count_label.SetLabel(str(new))

    def _on_move(self, from_label: int, to_label: int) -> None:
        result = self.session.dispatch(MoveCmd(from_label, to_label))
        self._set_message(
            "\n".join(result.lines)
            if result.lines
            else f"Moved {from_label} → {to_label}."
        )
        self._refresh()
        if self.session.is_won():
            self._on_win()

    def _on_relabel(self, labels: Tuple[int, int, int]) -> None:
        result = self.session.dispatch(RelabelCmd(labels))
        self._set_message("\n".join(result.lines))
        self._refresh()

    def _on_save(self, _evt) -> None:
        if not self.session.is_won():
            wx.MessageBox(
                "Save Current only works after winning a game. "
                "Keep playing — you'll be able to save once you finish.",
                "Can't save yet",
                wx.OK | wx.ICON_INFORMATION,
            )
            return
        with wx.TextEntryDialog(
            self,
            "Recipe name:",
            "Save Recipe",
            value=f"solve-{self.session.num_disks}",
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            name = dlg.GetValue().strip()
            if not name:
                return
            msg = self.session.save_recipe(name)
            self._set_message(msg)
            self._refresh_recipes(select=name)

    def _on_apply(self, _evt) -> None:
        name = self._selected_recipe_name()
        if not name:
            self._set_message("Select a recipe first.")
            return
        result = self.session.dispatch(ApplyCmd(name))
        self._set_message("\n".join(result.lines))
        self._refresh()
        if self.session.is_won():
            self._on_win()

    def _on_show(self, _evt) -> None:
        name = self._selected_recipe_name()
        if not name:
            self._set_message("Select a recipe first.")
            return
        result = self.session.dispatch(ShowCmd(name))
        wx.MessageBox(
            "\n".join(result.lines),
            f"Recipe '{name}'",
            wx.OK | wx.ICON_INFORMATION,
        )

    # --- State helpers ---------------------------------------------------

    def _new_game(self, n: int) -> None:
        self.session = GameSession(num_disks=n, registry=self.registry)
        self._refresh()

    def _on_win(self) -> None:
        """Lock down play actions but keep New Game and Save Current
        usable so the user can save the recipe or start over."""
        for btn in self.move_buttons.values():
            btn.Disable()
        for btn in self.relabel_buttons.values():
            btn.Disable()
        self.apply_btn.Disable()
        # Show Selected stays enabled — inspecting saved recipes is harmless
        # at any point in the game, including after winning.
        min_moves = self.session.min_moves()
        moves = self.session.current_moves
        text = f"Solved! {moves} moves (minimum {min_moves})."
        if moves == min_moves:
            text += "\nOptimal solution!"
        else:
            text += f"\n{moves - min_moves} more than the minimum."
        text += "\nClick 'Save Current Solution' to keep this as a recipe."
        self._set_message(text)

    def _on_board_resize(self, evt) -> None:
        evt.Skip()
        if self.session is not None:
            self._update_board()

    def _update_board(self) -> None:
        """Render the board into the panel, centred horizontally and
        bottom-aligned vertically (so it sits like the curses layout)."""
        lines = presenter.render(self.session.game, self.session.labelling)
        if not lines:
            self.board.SetValue("")
            return
        panel_w_px, panel_h_px = self.board.GetSize()
        char_w = max(1, self.board.GetCharWidth())
        line_h = max(1, self.board.GetCharHeight())
        visible_cols = max(1, panel_w_px // char_w)
        visible_rows = max(1, panel_h_px // line_h)

        line_width = len(
            lines[0]
        )  # presenter pads every line to the same width
        h_pad = max(0, (visible_cols - line_width) // 2)
        centred = [(" " * h_pad + line) for line in lines]
        # -1 of slack so the bottom line isn't sitting under the scrollbar
        v_pad = max(0, visible_rows - len(centred) - 1)
        self.board.SetValue("\n" * v_pad + "\n".join(centred))

    def _refresh(self) -> None:
        # Board
        self._update_board()
        # Status bar text
        a, b, c = (
            change_labels_on_pegs(self.session.labelling, i) + 1
            for i in range(3)
        )
        self.status_label.SetLabel(
            f"Discs: {self.session.num_disks}    "
            f"Labelling: {a} {b} {c}    "
            f"Moves: {self.session.current_moves}    "
            f"Recipes: {len(self.registry)}"
        )
        # Re-enable everything (a New Game resets after a win lockout)
        valid = set()
        for vm in self.session.game.move_options():
            f = (
                change_labels_on_pegs(self.session.labelling, vm.move.from_peg)
                + 1
            )
            t = (
                change_labels_on_pegs(self.session.labelling, vm.move.to_peg)
                + 1
            )
            valid.add((f, t))
        won = self.session.is_won()
        for pair, btn in self.move_buttons.items():
            btn.Enable(not won and pair in valid)
        # Highlight the active labelling by disabling its button so the
        # user can see which one they're under at a glance.
        current_labels = tuple(
            change_labels_on_pegs(self.session.labelling, i) + 1
            for i in range(3)
        )
        for labels, btn in self.relabel_buttons.items():
            btn.Enable(not won and labels != current_labels)
        self.apply_btn.Enable(not won)
        self.show_btn.Enable(True)
        self._refresh_recipes()
        self.panel.Layout()

    def _refresh_recipes(self, select: Optional[str] = None) -> None:
        names = self.registry.names()
        previous = self._selected_recipe_name()
        self.recipe_list.Clear()
        for name in names:
            recipe = self.registry.get(name)
            display = (
                f"{name}  ({recipe.disk_count} discs, "
                f"{len(recipe.default_moves)} moves)"
            )
            self.recipe_list.Append(display, clientData=name)
        chosen = select or previous
        if chosen and chosen in names:
            self.recipe_list.SetSelection(names.index(chosen))

    def _selected_recipe_name(self) -> Optional[str]:
        """Return the bare name behind whatever is selected, or None."""
        idx = self.recipe_list.GetSelection()
        if idx == wx.NOT_FOUND:
            return None
        return self.recipe_list.GetClientData(idx)

    def _set_message(self, text: str) -> None:
        self.message.SetValue(text)


def main() -> None:
    app = wx.App()
    frame = HanoiFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
