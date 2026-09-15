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
from collections.abc import Sequence
from typing import Optional

import wx
import wx.xrc

from .board_renderers import (
    BoardRenderer,
    GraphicsBoardRenderer,
    TextBoardRenderer,
)
from .commands import ApplyCmd, MoveCmd, RelabelCmd, ShowCmd
from .engine import GameSession
from .presenter import Labelling, change_labels_on_pegs
from .recipe import RecipeRegistry, rebinding, rebound_moves

MAX_DISKS = 10
DEFAULT_DISKS = 3

ALL_LABEL_PAIRS: tuple[tuple[int, int], ...] = (
    (1, 2),
    (1, 3),
    (2, 1),
    (2, 3),
    (3, 1),
    (3, 2),
)

ALL_RELABEL_PERMUTATIONS: tuple[tuple[int, int, int], ...] = (
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

    def _load_hanoi_xrc(self) -> wx.xrc.XmlResource:
        """Load hanoi.xrc into the global XmlResource exactly once, and return
        it. Both the menu bar and the panel are defined there; loading the file
        twice would duplicate XRC ids, so this is guarded and shared."""
        res = wx.xrc.XmlResource.Get()
        if not getattr(self, "_xrc_loaded", False):
            with importlib.resources.as_file(
                importlib.resources.files("hanoigame").joinpath("hanoi.xrc")
            ) as xrc_path:
                res.Load(str(xrc_path))
            self._xrc_loaded = True
        return res

    def _build_menu_bar(self) -> None:
        # The menu-bar STRUCTURE (menus, items, accelerators, radio groups)
        # lives in hanoi.xrc; here we only load it, bind each item by XRCID,
        # and cache the few MenuItems _refresh() toggles (the relabel radios
        # and the board-style radios).
        res = self._load_hanoi_xrc()
        menubar = res.LoadMenuBar("main_menubar")
        self.SetMenuBar(menubar)

        xrcid = wx.xrc.XRCID
        self.Bind(wx.EVT_MENU, self._on_new_game_prompt, id=xrcid("wxID_NEW"))
        self.Bind(
            wx.EVT_MENU, self._on_new_game_same, id=xrcid("game_new_same")
        )
        self.Bind(wx.EVT_MENU, lambda _e: self.Close(), id=xrcid("wxID_EXIT"))
        self.Bind(wx.EVT_MENU, self._on_about, id=xrcid("wxID_ABOUT"))
        self.Bind(
            wx.EVT_MENU,
            lambda _e: self._swap_renderer(TextBoardRenderer),
            id=xrcid("style_text"),
        )
        self.Bind(
            wx.EVT_MENU,
            lambda _e: self._swap_renderer(GraphicsBoardRenderer),
            id=xrcid("style_graphics"),
        )
        self.style_text_item = menubar.FindItemById(xrcid("style_text"))
        self.style_graphics_item = menubar.FindItemById(xrcid("style_graphics"))

        # Relabel: one NORMAL menu item per permutation (not radio — see the XRC
        # comment on why). Fetch each MenuItem and its base label (so _refresh can
        # mark the active one), and bind it to the handler.
        self.relabel_menu_items: dict = {}
        self.relabel_base_labels: dict = {}
        for labels in ALL_RELABEL_PERMUTATIONS:
            item_id = xrcid(
                f"relabel_{labels[0]}_{labels[1]}_{labels[2]}"
            )
            item = menubar.FindItemById(item_id)
            self.relabel_menu_items[labels] = item
            self.relabel_base_labels[labels] = item.GetItemLabel()
            self.Bind(
                wx.EVT_MENU,
                lambda _evt, lab=labels: self._on_relabel_menu(lab),
                id=item_id,
            )

    def _build_ui(self) -> None:
        # Load the panel layout from hanoi.xrc (already loaded once by
        # _build_menu_bar). Fonts, event bindings, and dynamic enable/disable
        # state are wired up in Python below; XRC only describes the static
        # widget tree.
        res = self._load_hanoi_xrc()
        self.panel = res.LoadPanel(self, "HanoiPanel")
        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(self.panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(frame_sizer)

        # Named controls
        self.board_slot = wx.xrc.XRCCTRL(self, "board_slot")
        self.recipe_list = wx.xrc.XRCCTRL(self, "recipe_list")
        self.save_btn = wx.xrc.XRCCTRL(self, "recipe_save")
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
        # Save Current Solution is the post-win save path (no auto-modal
        # — `_refresh` enables it iff `is_won()`).
        self.Bind(wx.EVT_BUTTON, self._on_save, id=wx.xrc.XRCID("recipe_save"))
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
        relabelled = self.session.labelling != Labelling.ONE_TWO_THREE
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
            # Teaching step: under a relabelling, show the same three-panel
            # rebinding for the single move the user just made, so they are
            # forced to see typed-label -> physical-peg. See
            # tasks/record-recipe-bindings-and-show-rebinding.md.
            if relabelled:
                self._show_rebinding_dialog(
                    title="Rebinding for your move",
                    intro=(
                        "You typed this move in the current (relabelled) "
                        "labels.\nHere is how each label maps to a physical "
                        "peg right now, and where your move actually went."
                    ),
                    left_header="Your move",
                    moves=[(from_label, to_label)],
                )
        self._refresh()
        if self.session.is_won():
            self._on_win()

    def _on_relabel_menu(self, labels: tuple[int, int, int]) -> None:
        # Surface the confirmation in the status bar (was silent) — so a menu
        # click gives visible feedback that the relabelling took, and so it's
        # obvious if the handler ever fails to fire.
        result = self.session.dispatch(RelabelCmd(labels))
        if result.lines:
            self._set_status(result.lines[0])
        self._refresh()

    def _on_apply(self, _evt) -> None:
        name = self._selected_recipe_name()
        if not name:
            self._set_status("Select a recipe first.")
            return
        relabelled = self.session.labelling != Labelling.ONE_TWO_THREE
        result = self.session.dispatch(ApplyCmd(name))
        # Apply streams multiple "step N: from -> to" lines; the board
        # animation already shows what happened, so summarise to a count.
        step_lines = [
            ln for ln in result.lines if ln.strip().startswith("step ")
        ]
        if step_lines:
            self._set_status(f"Applied '{name}' — {len(step_lines)} moves.")
        elif result.lines:
            self._set_status(result.lines[-1])
        # Teaching step: when the recipe was replayed under a relabelling, pop
        # up the three-panel local->global rebinding so the student sees why the
        # recorded solution's labels change. See
        # tasks/record-recipe-bindings-and-show-rebinding.md.
        recipe = self.session.registry.get(name)
        if relabelled and recipe is not None:
            self._show_rebinding_dialog(
                title=f"Rebinding for '{name}'",
                intro=(
                    "This recipe is written in labels 1, 2, 3. Because you "
                    "relabelled,\neach move is rebound to a physical peg — "
                    "the same solution, new labels."
                ),
                left_header="Recipe moves",
                moves=recipe.default_moves,
            )
        self._refresh()
        if self.session.is_won():
            self._on_win()

    def _show_rebinding_dialog(
        self,
        *,
        title: str,
        intro: str,
        left_header: str,
        moves: Sequence[tuple[int, int]],
    ) -> None:
        """Three-panel teaching view of moves made/replayed under a
        relabelling: the moves in their typed/stored labels (left), the
        label→peg rebinding key (middle), and the same moves rebound onto
        physical pegs (right). Left and right are monospace scroll lists that
        line up move-for-move — selecting a move on one side selects AND
        scrolls the other to match. Non-modal and in-session only (nothing
        persisted); a single dialog is reused so repeated moves don't pile up
        windows. Used for both `apply` (a whole recipe) and a single move."""
        # One reusable rebinding window: a fresh apply/move closes the previous
        # one instead of stacking dialogs (a plain move fires this on every
        # relabelled move, so stacking would bury the board in popups). The
        # handle is tracked lazily via getattr — no __init__ change needed — and
        # is None whenever none is open. Destroy() raises if the user already
        # closed it, hence the guard.
        prev = getattr(self, "_rebinding_dlg", None)
        if prev is not None:
            try:
                prev.Destroy()
            except RuntimeError:
                pass
            self._rebinding_dlg = None

        labelling = self.session.labelling
        left_items = [f"{i}: {a} → {b}" for i, (a, b) in enumerate(moves, 1)]
        right_items = [
            f"{i}: {fp} → {tp}"
            for i, (fp, tp) in enumerate(rebound_moves(moves, labelling), 1)
        ]
        key = [
            f"label {label} → peg {peg}"
            for label, peg in rebinding(labelling)
        ]

        # Layout (the three panels + Close) is RebindingDialog in hanoi.xrc;
        # here we only fetch the named controls and fill in the dynamic bits:
        # title, intro, the left header text, the key, the two lists, fonts,
        # the scroll-sync, and Close.
        dlg = self._load_hanoi_xrc().LoadDialog(self, "RebindingDialog")
        dlg.SetTitle(title)
        mono = wx.Font(
            12,
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )
        xrcctrl = wx.xrc.XRCCTRL
        xrcctrl(dlg, "rebind_intro").SetLabel(intro)
        xrcctrl(dlg, "rebind_left_header").SetLabel(left_header)
        key_text = xrcctrl(dlg, "rebind_key")
        key_text.SetLabel("\n".join(key))
        key_text.SetFont(mono)

        left_lb = xrcctrl(dlg, "rebind_left")
        right_lb = xrcctrl(dlg, "rebind_right")
        for listbox, items in ((left_lb, left_items), (right_lb, right_items)):
            listbox.SetFont(mono)
            listbox.Set(items)
            row_h = max(1, listbox.GetCharHeight())
            listbox.SetMinSize((210, row_h * 10 + 8))

        # Selecting a move selects the matching one on the other side AND
        # scrolls both so they line up. Both lists have the same number of
        # rows, so pinning the same first item aligns them exactly. (Programmatic
        # SetSelection does not fire EVT_LISTBOX, so there's no feedback loop.)
        def _sync(src: wx.ListBox, dst: wx.ListBox):
            def handler(_evt) -> None:
                i = src.GetSelection()
                if i == wx.NOT_FOUND:
                    return
                for lb in (src, dst):
                    if i >= lb.GetCount():
                        continue
                    lb.SetSelection(i)
                    # Scroll BOTH lists to put row i in the same place, so the
                    # matched moves line up visually. SetFirstItem pins the top
                    # row; not every wx port exposes it, so fall back to
                    # EnsureVisible. getattr avoids crashing if a method is
                    # absent (verify wx calls, don't assume — sizer-flag lesson).
                    set_first = getattr(lb, "SetFirstItem", None)
                    if set_first is not None:
                        set_first(i)
                    else:
                        ensure = getattr(lb, "EnsureVisible", None)
                        if ensure is not None:
                            ensure(i)

            return handler

        left_lb.Bind(wx.EVT_LISTBOX, _sync(left_lb, right_lb))
        right_lb.Bind(wx.EVT_LISTBOX, _sync(right_lb, left_lb))

        def _close(_evt) -> None:
            self._rebinding_dlg = None
            dlg.Destroy()

        dlg.Bind(wx.EVT_BUTTON, _close, id=wx.ID_CLOSE)
        dlg.Bind(wx.EVT_CLOSE, _close)
        dlg.Fit()
        dlg.Show()
        self._rebinding_dlg = dlg

    def _on_show(self, _evt) -> None:
        name = self._selected_recipe_name()
        if not name:
            self._set_status("Select a recipe first.")
            return
        result = self.session.dispatch(ShowCmd(name))
        self._show_recipe_dialog(name, result.lines)

    def _show_recipe_dialog(self, name: str, lines: list) -> None:
        """Scrollable list of recipe steps (layout: RecipeDialog in hanoi.xrc).
        Non-modal so the user can keep playing (or open a second recipe to
        compare) while it's on screen; a `wx.MessageBox` chokes on the
        multi-hundred-step recipes a large game can produce."""
        dlg = self._load_hanoi_xrc().LoadDialog(self, "RecipeDialog")
        dlg.SetTitle(f"Recipe '{name}'")
        listbox = wx.xrc.XRCCTRL(dlg, "recipe_steps")
        listbox.SetFont(
            wx.Font(
                12,
                wx.FONTFAMILY_TELETYPE,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        listbox.Set(list(lines))
        # Size the listbox to show ~10 rows; the dialog scrolls past that.
        # GetCharHeight is the line-height in the listbox's font.
        row_h = max(1, listbox.GetCharHeight())
        listbox.SetMinSize((360, row_h * 10 + 8))

        dlg.Bind(wx.EVT_BUTTON, lambda _e: dlg.Destroy(), id=wx.ID_CLOSE)
        dlg.Bind(wx.EVT_CLOSE, lambda _e: dlg.Destroy())
        dlg.Fit()
        dlg.Show()

    # --- State helpers ---------------------------------------------------

    def _new_game(self, n: int) -> None:
        self.session = GameSession(num_disks=n, registry=self.registry)
        self._refresh()

    def _on_win(self) -> None:
        """Set the status-bar winning message. Button state (Move /
        Relabel / Apply disabled, Save Current Solution enabled) is
        already handled in `_refresh`. No modal — the board stays
        visible and the user clicks Save Current Solution when they
        want."""
        min_moves = self.session.min_moves()
        moves = self.session.current_moves
        if moves == min_moves:
            verdict = "Optimal!"
        else:
            verdict = (
                f"{moves - min_moves} more than the minimum ({min_moves})."
            )
        self._set_status(
            f"Solved in {moves} moves — {verdict}  "
            "Click 'Save Current Solution' to keep it as a recipe."
        )

    def _on_save(self, _evt) -> None:
        # Button is only enabled when won; no need to re-check.
        self._save_recipe_with_prompt()

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

    def _swap_renderer(self, renderer_cls: type[BoardRenderer]) -> None:
        """Tear down the current board renderer and install a new one in
        the same slot. Game state is unchanged; the new renderer gets a
        fresh `update()` so it shows the current board immediately."""
        if isinstance(self.board_renderer, renderer_cls):
            return
        sizer = self.board_slot.GetSizer()
        sizer.Clear(delete_windows=True)
        self.board_renderer = renderer_cls(self.board_slot)
        sizer.Add(self.board_renderer.widget(), proportion=1, flag=wx.EXPAND)
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
        # Mark the active relabel item with a leading bullet (these are normal
        # menu items, not radios — see the XRC comment; a radio's checked state
        # is unreliable on wxGTK and, worse, swallows clicks on the item it
        # thinks is already active). Rewriting the label is display-only and
        # never emits an event, so the current peg-order is always shown and
        # every click always fires.
        for labels, item in self.relabel_menu_items.items():
            base = self.relabel_base_labels[labels]
            marker = "●  " if labels == current_labels else "     "
            item.SetItemLabel(marker + base)
            item.Enable(not won)
        self.apply_btn.Enable(not won)
        self.show_btn.Enable(True)
        self.save_btn.Enable(won)
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
