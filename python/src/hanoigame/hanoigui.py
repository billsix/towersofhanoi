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
Disc count and New Game live on the frame's menu bar; per-action
feedback lives on the frame's status bar. Same `engine.GameSession`
dispatcher as the CLI and curses, so behaviour stays consistent across
all three frontends.
"""

import importlib.resources
from typing import Optional, Tuple, Type

import wx
import wx.xrc

from .board_renderers import (
    BoardRenderer,
    GraphicsBoardRenderer,
    TextBoardRenderer,
)
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
        super().__init__(None, title="Towers of Hanoi", size=(1100, 650))
        self.registry = RecipeRegistry()
        self.session: Optional[GameSession] = None
        self.disc_count_value = DEFAULT_DISKS
        self.move_buttons: dict = {}
        self._build_menu_bar()
        self.CreateStatusBar(2)
        # Field 0 stretches (action feedback); field 1 is fixed-width for
        # the moves counter so it sits at the right edge of the bar.
        self.SetStatusWidths([-1, 140])
        self._build_ui()
        self._new_game(DEFAULT_DISKS)

    # --- UI construction --------------------------------------------------

    def _build_menu_bar(self) -> None:
        menubar = wx.MenuBar()

        game_menu = wx.Menu()
        new_item = game_menu.Append(
            wx.ID_NEW, "&New Game…\tCtrl+N", "Start a new game"
        )
        new_same_item = game_menu.Append(
            wx.ID_ANY,
            "New Game (Same &Size)\tCtrl+Shift+N",
            "Start a new game with the same disc count",
        )
        game_menu.AppendSeparator()
        quit_item = game_menu.Append(wx.ID_EXIT, "&Quit\tCtrl+Q", "Quit")
        menubar.Append(game_menu, "&Game")

        # Relabel: one radio item per permutation. The currently-active
        # labelling is checked, set in _refresh().
        relabel_menu = wx.Menu()
        self.relabel_menu_items: dict = {}
        for labels in ALL_RELABEL_PERMUTATIONS:
            label_text = f"{labels[0]}    {labels[1]}    {labels[2]}"
            item = relabel_menu.AppendRadioItem(wx.ID_ANY, label_text)
            self.relabel_menu_items[labels] = item
            self.Bind(
                wx.EVT_MENU,
                lambda _evt, lab=labels: self._on_relabel_menu(lab),
                item,
            )
        menubar.Append(relabel_menu, "&Relabel pegs")

        # View: board-style radio submenu. Text view stays pixel-identical
        # to CLI / curses; Graphics is a procedurally-drawn 2D view.
        view_menu = wx.Menu()
        style_menu = wx.Menu()
        self.style_text_item = style_menu.AppendRadioItem(wx.ID_ANY, "&Text")
        self.style_graphics_item = style_menu.AppendRadioItem(
            wx.ID_ANY, "&Graphics"
        )
        view_menu.AppendSubMenu(style_menu, "Board &Style")
        menubar.Append(view_menu, "&View")

        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, "&About")
        menubar.Append(help_menu, "&Help")

        self.SetMenuBar(menubar)
        self.Bind(wx.EVT_MENU, self._on_new_game_prompt, new_item)
        self.Bind(wx.EVT_MENU, self._on_new_game_same, new_same_item)
        self.Bind(wx.EVT_MENU, lambda _e: self.Close(), quit_item)
        self.Bind(wx.EVT_MENU, self._on_about, about_item)
        self.Bind(
            wx.EVT_MENU,
            lambda _e: self._swap_renderer(TextBoardRenderer),
            self.style_text_item,
        )
        self.Bind(
            wx.EVT_MENU,
            lambda _e: self._swap_renderer(GraphicsBoardRenderer),
            self.style_graphics_item,
        )

    def _build_ui(self) -> None:
        # Load the panel layout from hanoi.xrc. Fonts, event bindings, and
        # dynamic enable/disable state are wired up in Python below; XRC
        # only describes the static widget tree.
        res = wx.xrc.XmlResource.Get()
        with importlib.resources.as_file(
            importlib.resources.files("hanoigame").joinpath("hanoi.xrc")
        ) as xrc_path:
            res.Load(str(xrc_path))
        self.panel = res.LoadPanel(self, "HanoiPanel")
        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(self.panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(frame_sizer)

        # Named controls
        self.board_slot = wx.xrc.XRCCTRL(self, "board_slot")
        self.recipe_list = wx.xrc.XRCCTRL(self, "recipe_list")
        self.apply_btn = wx.xrc.XRCCTRL(self, "recipe_apply")
        self.show_btn = wx.xrc.XRCCTRL(self, "recipe_show")

        for from_label, to_label in ALL_LABEL_PAIRS:
            self.move_buttons[(from_label, to_label)] = wx.xrc.XRCCTRL(
                self, f"move_{from_label}_{to_label}"
            )

        self.recipe_list.SetFont(
            wx.Font(
                12,
                wx.FONTFAMILY_TELETYPE,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )

        # board_slot holds whichever BoardRenderer is active. Graphics
        # is the default — text view remains available under View →
        # Board Style for parity with CLI / curses output.
        self.board_slot.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.board_renderer: BoardRenderer = GraphicsBoardRenderer(
            self.board_slot
        )
        self.board_slot.GetSizer().Add(
            self.board_renderer.widget(), proportion=1, flag=wx.EXPAND
        )
        self.style_graphics_item.Check(True)

        # Recipe button bindings + double-click on the list as a Show
        # shortcut so a curious user can flip through recipes quickly.
        self.Bind(
            wx.EVT_BUTTON, self._on_apply, id=wx.xrc.XRCID("recipe_apply")
        )
        self.Bind(wx.EVT_BUTTON, self._on_show, id=wx.xrc.XRCID("recipe_show"))
        self.recipe_list.Bind(wx.EVT_LISTBOX_DCLICK, self._on_show)

        # Move button bindings — lambda captures the from/to pair.
        for from_label, to_label in ALL_LABEL_PAIRS:
            self.Bind(
                wx.EVT_BUTTON,
                lambda _evt, f=from_label, t=to_label: self._on_move(f, t),
                id=wx.xrc.XRCID(f"move_{from_label}_{to_label}"),
            )

        self.Center()

    # --- Event handlers --------------------------------------------------

    def _on_new_game_prompt(self, _evt) -> None:
        with wx.NumberEntryDialog(
            self,
            "How many discs?",
            "Discs:",
            "New Game",
            self.disc_count_value,
            1,
            MAX_DISKS,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            self.disc_count_value = dlg.GetValue()
        self._new_game(self.disc_count_value)
        # Silent: the user just picked the disc count; the board renders
        # the result. Nothing to tell them they don't already know.
        self._set_status("")

    def _on_new_game_same(self, _evt) -> None:
        self._new_game(self.disc_count_value)
        self._set_status("")

    def _on_about(self, _evt) -> None:
        wx.MessageBox(
            "Towers of Hanoi\n"
            "\n"
            "A teaching tool for solving Hanoi by hand: solve small, "
            "relabel pegs, replay.\n"
            "\n"
            "Shared model + dispatcher with the CLI and curses frontends.",
            "About Towers of Hanoi",
            wx.OK | wx.ICON_INFORMATION,
        )

    def _on_move(self, from_label: int, to_label: int) -> None:
        result = self.session.dispatch(MoveCmd(from_label, to_label))
        if result.lines:
            # Illegal-move message — single line in status, full text in
            # a popup so the explanation isn't lost.
            self._set_status(result.lines[0])
            if len(result.lines) > 1:
                wx.MessageBox(
                    "\n".join(result.lines),
                    "Illegal move",
                    wx.OK | wx.ICON_WARNING,
                )
        else:
            self._set_status(f"Moved {from_label} → {to_label}.")
        self._refresh()
        if self.session.is_won():
            self._on_win()

    def _on_relabel_menu(self, labels: Tuple[int, int, int]) -> None:
        self.session.dispatch(RelabelCmd(labels))
        # Silent: the menu's own radio check + recoloured board confirm.
        self._refresh()

    def _on_apply(self, _evt) -> None:
        name = self._selected_recipe_name()
        if not name:
            self._set_status("Select a recipe first.")
            return
        result = self.session.dispatch(ApplyCmd(name))
        # Apply streams multiple "step N: from -> to" lines; the board
        # animation already shows what happened, so summarise to a count.
        step_lines = [ln for ln in result.lines if ln.startswith("step ")]
        if step_lines:
            self._set_status(f"Applied '{name}' — {len(step_lines)} moves.")
        elif result.lines:
            self._set_status(result.lines[-1])
        self._refresh()
        if self.session.is_won():
            self._on_win()

    def _on_show(self, _evt) -> None:
        name = self._selected_recipe_name()
        if not name:
            self._set_status("Select a recipe first.")
            return
        result = self.session.dispatch(ShowCmd(name))
        self._show_recipe_dialog(name, result.lines)

    def _show_recipe_dialog(self, name: str, lines: list) -> None:
        """Scrollable list of recipe steps — a `wx.MessageBox` chokes on
        the multi-hundred-step recipes a large game can produce. The
        dialog is non-modal so the user can keep playing (or open a
        second recipe to compare) while it's on screen."""
        dlg = wx.Dialog(
            self,
            title=f"Recipe '{name}'",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        listbox = wx.ListBox(dlg, choices=lines, style=wx.LB_SINGLE)
        listbox.SetFont(
            wx.Font(
                12,
                wx.FONTFAMILY_TELETYPE,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        # Size the listbox to show ~10 rows; the dialog scrolls past
        # that. GetCharHeight is the line-height in the listbox's font.
        row_h = max(1, listbox.GetCharHeight())
        listbox.SetMinSize((360, row_h * 10 + 8))

        btn = wx.Button(dlg, wx.ID_CLOSE, "Close")
        btn.Bind(wx.EVT_BUTTON, lambda _e: dlg.Destroy())
        dlg.Bind(wx.EVT_CLOSE, lambda _e: dlg.Destroy())

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(listbox, proportion=1, flag=wx.EXPAND | wx.ALL, border=8)
        sizer.Add(btn, flag=wx.ALIGN_CENTER | wx.BOTTOM, border=8)
        dlg.SetSizerAndFit(sizer)
        dlg.Show()

    # --- State helpers ---------------------------------------------------

    def _new_game(self, n: int) -> None:
        self.session = GameSession(num_disks=n, registry=self.registry)
        self._refresh()

    def _on_win(self) -> None:
        """Lock down play actions, then offer to save the solution as a
        recipe. New Game / Show stay reachable from the menu and the
        recipe sidebar. (`_refresh` already disables Move buttons,
        Apply, and the Relabel menu items when `won` is true; this is
        belt-and-braces in case anything is called out of order.)"""
        for btn in self.move_buttons.values():
            btn.Disable()
        for item in self.relabel_menu_items.values():
            item.Enable(False)
        self.apply_btn.Disable()

        min_moves = self.session.min_moves()
        moves = self.session.current_moves
        if moves == min_moves:
            verdict = "Optimal!"
        else:
            verdict = f"{moves - min_moves} more than the minimum ({min_moves})."
        self._set_status(f"Solved in {moves} moves — {verdict}")

        dlg = wx.MessageDialog(
            self,
            f"Solved in {moves} moves.\n{verdict}\n\n"
            "Save this solution as a recipe so you can apply it later?",
            "Solved!",
            wx.YES_NO | wx.ICON_INFORMATION,
        )
        dlg.SetYesNoLabels("Save as recipe…", "Not now")
        try:
            if dlg.ShowModal() == wx.ID_YES:
                self._save_recipe_with_prompt()
        finally:
            dlg.Destroy()

    def _save_recipe_with_prompt(self) -> None:
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
            self._set_status(msg)
            self._refresh_recipes(select=name)

    def _swap_renderer(self, renderer_cls: Type[BoardRenderer]) -> None:
        """Tear down the current board renderer and install a new one in
        the same slot. Game state is unchanged; the new renderer gets a
        fresh `update()` so it shows the current board immediately."""
        if isinstance(self.board_renderer, renderer_cls):
            return
        sizer = self.board_slot.GetSizer()
        sizer.Clear(delete_windows=True)
        self.board_renderer = renderer_cls(self.board_slot)
        sizer.Add(
            self.board_renderer.widget(), proportion=1, flag=wx.EXPAND
        )
        self.board_slot.Layout()
        if self.session is not None:
            self.board_renderer.update(
                self.session.game, self.session.labelling
            )

    def _refresh(self) -> None:
        self.board_renderer.update(self.session.game, self.session.labelling)
        won = self.session.is_won()
        self.SetStatusText(f"Moves: {self.session.current_moves}", 1)

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
        for pair, btn in self.move_buttons.items():
            btn.Enable(not won and pair in valid)

        current_labels = tuple(
            change_labels_on_pegs(self.session.labelling, i) + 1
            for i in range(3)
        )
        # Check the active radio item; sibling radios auto-uncheck.
        self.relabel_menu_items[current_labels].Check(True)
        for item in self.relabel_menu_items.values():
            item.Enable(not won)
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

    def _set_status(self, text: str) -> None:
        self.SetStatusText(text)


def main() -> None:
    app = wx.App()
    frame = HanoiFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
