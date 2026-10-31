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

Organized around the learner's journey (feature-spec.md §3.5, Apple-HIG
progressive disclosure), in three tiers:

- **Tier 1 — always visible:** the board (text or 2D-graphics), the six move
  buttons (auto-enabled from `game.move_options()`), an always-present goal
  line in the status bar, a dismissible "How to Play" panel (shown on first
  run, reopenable from the Help menu), and an always-visible move-history
  panel (every move this game in the default 1-2-3 physical labels).
- **Tier 2 — unlocked at the first win (for the session):** the Relabel pegs
  menu and saving a recipe. Gated before then by disabling the menus ("dim,
  don't remove").
- **Tier 3 — in the Recipe menu, out of the workspace:** each saved recipe is a
  submenu that expands to View / Apply, plus the three-panel rebinding view.

New Game / disc count and board style live on the menu bar; per-action feedback
and the moves counter live on the two-field status bar. Same
`engine.GameSession` dispatcher as the CLI and curses, so behaviour stays
consistent across all front-ends.

The redesign is programmatic (recipe sidebar hidden, Recipe/View menu items and
the history/goal/how-to panels built in Python) so the shared `ui/hanoi.xrc` —
also loaded by the C++ and Rust wx front-ends — is untouched in this oracle
phase; fanning the flow out to the other UIs (and settling the shared XRC form)
is a separate task.
"""

import importlib.resources
from collections.abc import Callable, Sequence

import wx
import wx.xrc

from .board_renderers import (
    BoardRenderer,
    GraphicsBoardRenderer,
    TextBoardRenderer,
)
from .commands import ApplyCmd, MoveCmd, RelabelCmd, ShowCmd
from .engine import DispatchResult, GameSession
from .hanoimodel import ValidMove
from .presenter import Labelling, change_labels_on_pegs, format_move_tally
from .recipe import Recipe, RecipeRegistry, rebinding, rebound_moves

MAX_DISKS: int = 10
DEFAULT_DISKS: int = 3

HOWTO_TEXT: str = (
    "Move the whole stack of discs from peg 1 to peg 3.\n"
    "• Move one disc at a time — always the top disc of a peg.\n"
    "• Never place a larger disc on a smaller one.\n"
    "\n"
    "The method this teaches: solve a SMALL stack, then RELABEL the pegs to\n"
    'reuse that solution for a bigger stack — "solve small, relabel,'
    ' replay."\n'
    "Relabelling and saved recipes unlock after your first win."
)

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

# Config (wx.Config) key: show the How-to-Play panel on launch. Set False by
# the panel's "Don't show this again" checkbox; re-shown any time from Help.
CONFIG_SHOW_HOWTO: str = "show_howto_on_start"

_DISC_FILL: wx.Colour = wx.Colour(210, 210, 215)
_DISC_EDGE: wx.Colour = wx.Colour(30, 30, 40)
_OK_ACCENT: wx.Colour = wx.Colour(40, 150, 60)
_NO_ACCENT: wx.Colour = wx.Colour(200, 55, 55)


class _LegalMoveDiagram(wx.Panel):
    """A small figure teaching the one rule: a smaller disc may rest on a
    larger one (left, allowed); a larger disc may never rest on a smaller one
    (right, forbidden). It illustrates the *rule*, not a screenshot of the app
    — the live board is the app's own best picture (Apple-HIG active
    assistance: teach the thing, point at the real object)."""

    def __init__(self, parent: wx.Window) -> None:
        """Build a fixed-size drawing panel and bind its paint handler."""
        super().__init__(parent, size=wx.Size(300, 108))
        self.SetMinSize(wx.Size(300, 108))
        self.Bind(wx.EVT_PAINT, self._on_paint)

    def _on_paint(self, _evt: wx.PaintEvent) -> None:
        """Draw the allowed example (left half) and forbidden one (right)."""
        dc: wx.PaintDC = wx.PaintDC(self)
        gc: wx.GraphicsContext | None = wx.GraphicsContext.Create(dc)
        if gc is None:
            return
        width: int = self.GetClientSize().width
        half: float = width / 2.0
        self._draw_example(gc, 0.0, half, legal=True)
        self._draw_example(gc, half, half, legal=False)

    def _draw_example(
        self, gc: wx.GraphicsContext, x0: float, width: float, *, legal: bool
    ) -> None:
        """Draw one two-disc stack centred in [x0, x0+width]: wide-under-narrow
        when `legal`, else narrow-under-wide struck through, with a caption."""
        cx: float = x0 + width / 2.0
        disc_h: float = 16.0
        top_y: float = 42.0
        big_w: float = 78.0
        small_w: float = 42.0
        bottom_w: float = big_w if legal else small_w
        upper_w: float = small_w if legal else big_w
        accent: wx.Colour = _OK_ACCENT if legal else _NO_ACCENT

        gc.SetPen(wx.Pen(_DISC_EDGE, 1))
        gc.SetBrush(wx.Brush(_DISC_FILL))
        w: float
        y: float
        for w, y in ((bottom_w, top_y + disc_h), (upper_w, top_y)):
            gc.DrawRoundedRectangle(cx - w / 2.0, y, w, disc_h, 4.0)

        if not legal:
            gc.SetPen(wx.Pen(accent, 3))
            gc.StrokeLine(
                cx - big_w / 2.0,
                top_y - 4.0,
                cx + big_w / 2.0,
                top_y + disc_h + 4.0,
            )

        caption: str = (
            "✓  smaller on larger" if legal else "✗  larger on smaller"
        )
        gc.SetFont(gc.CreateFont(self.GetFont(), accent))
        text_w: float
        text_w, _th, _d, _e = gc.GetFullTextExtent(caption)
        gc.DrawText(caption, cx - text_w / 2.0, 84.0)


class HanoiFrame(wx.Frame):
    """The main application window: board, controls, menu, and status bar.

    Owns the cross-game `RecipeRegistry` and the current `GameSession`, and
    swaps between the text and graphics board renderers on demand.
    """

    def __init__(self) -> None:
        """Build the menu bar, status bar, panel, and start a default game."""
        super().__init__(None, title="Towers of Hanoi", size=wx.Size(1100, 650))
        self.registry = RecipeRegistry()
        # Assigned by `_new_game`, which __init__ calls below before the frame
        # is ever shown, so every handler sees a live session — hence the
        # attribute is declared non-Optional.
        self.session: GameSession
        self.disc_count_value = DEFAULT_DISKS
        self.move_buttons: dict[tuple[int, int], wx.Window] = {}
        # Tier-2 gating (feature-spec §3.5): relabel + recipes unlock at the
        # first win and stay unlocked for the rest of the session.
        self._won_once: bool = False
        # The always-visible Tier-1 move-history panel, built in `_build_ui`.
        self._history_panel: wx.Panel | None = None
        self._history_list: wx.ListBox | None = None
        self._history_header: wx.StaticText | None = None
        # Tier-1 onboarding: the goal line lives in the status bar (set by
        # `_update_goal`); "How to Play" is a dismissible panel built in
        # `_build_ui`, shown on first run and reopenable from the Help menu.
        self._config: wx.ConfigBase = wx.ConfigBase.Get()
        self._howto_panel: wx.Panel | None = None
        self._howto_dont_show: wx.CheckBox | None = None
        # Menu-bar positions of the Tier-2 menus `_refresh` enables/disables.
        self._relabel_menu_pos: int = -1
        self._recipe_menu_pos: int = -1
        # Saved-recipe names currently reflected in the Recipe menu, so
        # `_refresh` rebuilds its submenus only when the set actually changed.
        self._recipe_menu_names: list[str] = []
        self._build_menu_bar()
        self.CreateStatusBar(3)
        # Field 0 = the persistent goal line; field 1 stretches for action
        # feedback; field 2 is fixed-width for the moves counter at the right.
        self.SetStatusWidths([-1, -2, 140])
        self._build_ui()
        self._new_game(DEFAULT_DISKS)

    # --- UI construction --------------------------------------------------

    def _load_hanoi_xrc(self) -> wx.xrc.XmlResource:
        """Load hanoi.xrc into the global XmlResource exactly once, and return
        it. Both the menu bar and the panel are defined there; loading the file
        twice would duplicate XRC ids, so this is guarded and shared."""
        res: wx.xrc.XmlResource = wx.xrc.XmlResource.Get()
        if not getattr(self, "_xrc_loaded", False):
            with importlib.resources.as_file(
                importlib.resources.files("hanoigame").joinpath("hanoi.xrc")
            ) as xrc_path:
                res.Load(str(xrc_path))
            self._xrc_loaded = True
        return res

    def _build_menu_bar(self) -> None:
        """Load the menu bar from XRC and bind every item by XRCID."""
        # The menu-bar STRUCTURE (menus, items, accelerators, radio groups)
        # lives in hanoi.xrc; here we only load it, bind each item by XRCID,
        # and cache the few MenuItems _refresh() toggles (the relabel radios
        # and the board-style radios).
        res: wx.xrc.XmlResource = self._load_hanoi_xrc()
        menubar: wx.MenuBar = res.LoadMenuBar("main_menubar")
        self.SetMenuBar(menubar)

        xrcid: Callable[..., int] = wx.xrc.XRCID
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
        # comment on why). Fetch each MenuItem and its base label (so _refresh
        # can mark the active one), and bind it to the handler.
        self.relabel_menu_items: dict[tuple[int, int, int], wx.MenuItem] = {}
        self.relabel_base_labels: dict[tuple[int, int, int], str] = {}
        labels: tuple[int, int, int]
        for labels in ALL_RELABEL_PERMUTATIONS:
            item_id: int = xrcid(f"relabel_{labels[0]}_{labels[1]}_{labels[2]}")
            item: wx.MenuItem = menubar.FindItemById(item_id)
            self.relabel_menu_items[labels] = item
            self.relabel_base_labels[labels] = item.GetItemLabel()
            self.Bind(
                wx.EVT_MENU,
                lambda _evt, lab=labels: self._on_relabel_menu(lab),
                id=item_id,
            )

        # Recipe menu (Tier 3, feature-spec §3.5) — recipes live here, not in
        # the main workspace. "Save Current Solution" (Ctrl+S) is the fixed
        # head; below a separator, `_rebuild_recipe_menu` lists each SAVED
        # recipe as a submenu expanding to View / Apply, so the user points at
        # the recipe itself rather than an abstract "Apply…/Show…/List…" verb
        # that then pops a chooser (tasks/recipe-menu-direct-recipes.md). Built
        # programmatically so the shared ui/hanoi.xrc (also loaded by the
        # C++/Rust wx front-ends) is untouched this phase.
        self._recipe_menu: wx.Menu = wx.Menu()
        self._recipe_save_item: wx.MenuItem = self._recipe_menu.Append(
            wx.ID_ANY,
            "&Save Current Solution\tCtrl+S",
            "Save the just-won solution as a reusable recipe",
        )
        self._recipe_menu.AppendSeparator()
        # Insert Recipe after Relabel: Game, Relabel, Recipe, View, Help.
        self._relabel_menu_pos = menubar.FindMenu("Relabel pegs")
        self._recipe_menu_pos = self._relabel_menu_pos + 1
        menubar.Insert(self._recipe_menu_pos, self._recipe_menu, "&Recipe")
        self.Bind(wx.EVT_MENU, self._on_save, id=self._recipe_save_item.GetId())
        self._rebuild_recipe_menu()

        # View menu: add the always-visible move-history toggle and the
        # How-to-play toggle to the existing (XRC) View menu.
        view_pos: int = menubar.FindMenu("View")
        view_menu: wx.Menu = menubar.GetMenu(view_pos)
        view_menu.AppendSeparator()
        self._history_toggle: wx.MenuItem = view_menu.AppendCheckItem(
            wx.ID_ANY,
            "Move &history\tCtrl+H",
            "Show the running list of moves in default 1-2-3 labels",
        )
        self._history_toggle.Check(True)
        self._howto_toggle: wx.MenuItem = view_menu.AppendCheckItem(
            wx.ID_ANY, "How to &play", "Show the How-to-Play panel"
        )
        self._howto_toggle.Check(self._config.ReadBool(CONFIG_SHOW_HOWTO, True))
        self.Bind(
            wx.EVT_MENU,
            self._on_toggle_history,
            id=self._history_toggle.GetId(),
        )
        self.Bind(
            wx.EVT_MENU, self._on_toggle_howto, id=self._howto_toggle.GetId()
        )

        # Help → How to Play: reopen the Tier-1 onboarding panel at any time
        # (recognition over recall — the learner never has to remember how to
        # summon it). Added programmatically so the shared ui/hanoi.xrc Help
        # menu (also used by the C++/Rust wx front-ends) is untouched here.
        help_pos: int = menubar.FindMenu("Help")
        if help_pos >= 0:
            help_menu: wx.Menu = menubar.GetMenu(help_pos)
            self._help_howto_item: wx.MenuItem = help_menu.Insert(
                0,
                wx.ID_ANY,
                "How to &Play",
                "Show the goal and the rules of the game",
            )
            help_menu.InsertSeparator(1)
            self.Bind(
                wx.EVT_MENU,
                self._on_help_howto,
                id=self._help_howto_item.GetId(),
            )

    def _build_ui(self) -> None:
        """Lay out the window: the XRC board panel (recipe sidebar hidden),
        wrapped with the Tier-1 onboarding (goal + How to play) above it and the
        always-visible move-history panel to its right."""
        res: wx.xrc.XmlResource = self._load_hanoi_xrc()
        self.panel = res.LoadPanel(self, "HanoiPanel")

        # Named controls from the XRC panel.
        self.board_slot = wx.xrc.XRCCTRL(self, "board_slot")
        from_label: int
        to_label: int
        for from_label, to_label in ALL_LABEL_PAIRS:
            self.move_buttons[(from_label, to_label)] = wx.xrc.XRCCTRL(
                self, f"move_{from_label}_{to_label}"
            )

        # Tier 3: hide the in-panel recipe sidebar — recipes move to the Recipe
        # menu (feature-spec §3.5). The shared XRC still defines these controls
        # for the other wx front-ends, so we only hide them here.
        self._hide_recipe_sidebar()

        # board_slot holds whichever BoardRenderer is active. Graphics is the
        # default — text view remains under View → Board Style for parity with
        # the CLI / curses output.
        self.board_slot.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.board_renderer: BoardRenderer = GraphicsBoardRenderer(
            self.board_slot
        )
        self.board_slot.GetSizer().Add(
            self.board_renderer.widget(), proportion=1, flag=wx.EXPAND
        )
        self.style_graphics_item.Check(True)
        self._wire_board_interaction()

        # Move button bindings — lambda captures the from/to pair.
        for from_label, to_label in ALL_LABEL_PAIRS:
            self.Bind(
                wx.EVT_BUTTON,
                lambda _evt, f=from_label, t=to_label: self._on_move(f, t),
                id=wx.xrc.XRCID(f"move_{from_label}_{to_label}"),
            )

        # Frame layout: the How-to-Play panel on top (hidden if the user chose
        # "don't show again"), then [board panel | history panel].
        self._howto_panel = self._build_howto_panel()
        self._history_panel = self._build_history_panel()
        row: wx.BoxSizer = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(self.panel, proportion=1, flag=wx.EXPAND)
        row.Add(
            self._history_panel,
            proportion=0,
            flag=wx.EXPAND | wx.TOP | wx.BOTTOM | wx.RIGHT,
            border=6,
        )
        frame_sizer: wx.BoxSizer = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(
            self._howto_panel, proportion=0, flag=wx.EXPAND | wx.ALL, border=6
        )
        frame_sizer.Add(row, proportion=1, flag=wx.EXPAND)
        self.SetSizer(frame_sizer)
        # First-run: show unless the user has dismissed it with "don't show
        # again". The View → How to play check item mirrors this state.
        self._howto_panel.Show(self._config.ReadBool(CONFIG_SHOW_HOWTO, True))
        self.Center()

    def _hide_recipe_sidebar(self) -> None:
        """Collapse the XRC panel's right-hand recipe sidebar (list + buttons);
        recipes move to the Recipe menu. The widgets stay defined in the shared
        XRC for the other wx UIs, so here we only hide the whole Recipes box."""
        recipe_list: wx.Window = wx.xrc.XRCCTRL(self, "recipe_list")
        box_sizer: wx.Sizer | None = recipe_list.GetContainingSizer()
        if box_sizer is None:
            return
        if isinstance(box_sizer, wx.StaticBoxSizer):
            box_sizer.GetStaticBox().Hide()
        top: wx.Sizer | None = self.panel.GetSizer()
        if top is None:
            return
        row_item: wx.SizerItem | None = top.GetItem(0)
        row: wx.Sizer | None = row_item.GetSizer() if row_item else None
        if row is not None:
            row.Hide(box_sizer, recursive=True)
        self.panel.Layout()

    def _build_howto_panel(self) -> wx.Panel:
        """Build the dismissible 'How to Play' panel: a heading, the rules
        text, a small legal/illegal-move diagram, a 'Don't show this again'
        checkbox, and a 'Got it' close button. Shown on first run and
        reopenable from Help → How to Play; the goal itself lives in the status
        bar. One source of truth — it supersedes the old goal banner and
        collapsible pane (feature-spec §3.5 onboarding)."""
        panel: wx.Panel = wx.Panel(self, style=wx.BORDER_SIMPLE)
        heading: wx.StaticText = wx.StaticText(panel, label="How to Play")
        heading_font: wx.Font = heading.GetFont()
        heading_font.MakeBold()
        heading_font.SetPointSize(heading_font.GetPointSize() + 2)
        heading.SetFont(heading_font)

        body: wx.StaticText = wx.StaticText(panel, label=HOWTO_TEXT)
        diagram: _LegalMoveDiagram = _LegalMoveDiagram(panel)

        self._howto_dont_show = wx.CheckBox(
            panel, label="Don't show this again"
        )
        self._howto_dont_show.SetValue(
            not self._config.ReadBool(CONFIG_SHOW_HOWTO, True)
        )
        self._howto_dont_show.Bind(wx.EVT_CHECKBOX, self._on_howto_dont_show)
        got_it: wx.Button = wx.Button(panel, label="Got it")
        got_it.Bind(wx.EVT_BUTTON, lambda _e: self._dismiss_howto())

        text_col: wx.BoxSizer = wx.BoxSizer(wx.VERTICAL)
        text_col.Add(heading, proportion=0, flag=wx.BOTTOM, border=6)
        text_col.Add(body, proportion=0)
        top_row: wx.BoxSizer = wx.BoxSizer(wx.HORIZONTAL)
        top_row.Add(
            text_col, proportion=1, flag=wx.EXPAND | wx.RIGHT, border=12
        )
        top_row.Add(diagram, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL)

        foot_row: wx.BoxSizer = wx.BoxSizer(wx.HORIZONTAL)
        foot_row.Add(
            self._howto_dont_show,
            proportion=0,
            flag=wx.ALIGN_CENTER_VERTICAL,
        )
        foot_row.AddStretchSpacer()
        foot_row.Add(got_it, proportion=0)

        panel_sizer: wx.BoxSizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(
            top_row, proportion=0, flag=wx.EXPAND | wx.ALL, border=8
        )
        panel_sizer.Add(
            foot_row,
            proportion=0,
            flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
            border=8,
        )
        panel.SetSizer(panel_sizer)
        return panel

    def _build_history_panel(self) -> wx.Panel:
        """Tier-1 always-visible move history: every move this game in the
        default 1-2-3 (physical) labels, with a live count vs the optimal
        2^N-1. Populated by `_update_history` from `recorder.default_moves`."""
        panel: wx.Panel = wx.Panel(self)
        mono: wx.Font = wx.Font(
            12,
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )
        title: wx.StaticText = wx.StaticText(panel, label="Move history")
        title_font: wx.Font = title.GetFont()
        title_font.MakeBold()
        title.SetFont(title_font)
        self._history_header = wx.StaticText(panel, label="")
        self._history_list = wx.ListBox(panel)
        self._history_list.SetFont(mono)
        row_h: int = max(1, self._history_list.GetCharHeight())
        self._history_list.SetMinSize(wx.Size(240, row_h * 12 + 8))
        sizer: wx.BoxSizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(title, proportion=0, flag=wx.ALL, border=6)
        sizer.Add(
            self._history_header,
            proportion=0,
            flag=wx.LEFT | wx.RIGHT | wx.BOTTOM,
            border=6,
        )
        sizer.Add(
            self._history_list,
            proportion=1,
            flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
            border=6,
        )
        panel.SetSizer(sizer)
        return panel

    # --- Event handlers --------------------------------------------------

    def _on_new_game_prompt(self, _evt: wx.CommandEvent) -> None:
        """Ask for a disc count, then start a new game with it."""
        dlg: wx.NumberEntryDialog
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

    def _on_new_game_same(self, _evt: wx.CommandEvent) -> None:
        """Restart with the same disc count as the current game."""
        self._new_game(self.disc_count_value)
        self._set_status("")

    def _on_about(self, _evt: wx.CommandEvent) -> None:
        """Show the About box (a stock message dialog)."""
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

    def _wire_board_interaction(self) -> None:
        """If the active board renderer supports disc dragging, point its drop
        callback at `_on_board_drop` (the move buttons stay as a parallel,
        keyboard/screen-reader-accessible path — kept for the spike)."""
        set_cb: Callable[[Callable[[int, int], None]], None] | None = getattr(
            self.board_renderer, "set_move_callback", None
        )
        if set_cb is not None:
            set_cb(self._on_board_drop)

    def _on_board_drop(self, from_peg: int, to_peg: int) -> None:
        """Drop handler: physical pegs -> current labels -> the same dispatch
        path as a move button (illegal-move popup, rebinding dialog, win)."""
        from_label: int = (
            change_labels_on_pegs(self.session.labelling, from_peg) + 1
        )
        to_label: int = (
            change_labels_on_pegs(self.session.labelling, to_peg) + 1
        )
        self._on_move(from_label, to_label)

    def _on_move(self, from_label: int, to_label: int) -> None:
        """Dispatch a move button; on success under a relabelling, show the
        single-move rebinding dialog, then refresh and check for a win."""
        relabelled: bool = self.session.labelling != Labelling.ONE_TWO_THREE
        result: DispatchResult = self.session.dispatch(
            MoveCmd(from_label, to_label)
        )
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
        """Apply a relabel chosen from the menu and refresh the board."""
        # Surface the confirmation in the status bar (was silent) — so a menu
        # click gives visible feedback that the relabelling took, and so it's
        # obvious if the handler ever fails to fire.
        result: DispatchResult = self.session.dispatch(RelabelCmd(labels))
        if result.lines:
            self._set_status(result.lines[0])
        self._refresh()

    def _apply_recipe_by_name(self, name: str) -> None:
        """Replay `name`; under a relabelling, show the three-panel rebinding
        dialog for the whole recipe (the teaching moment, feature-spec §4.8)."""
        relabelled: bool = self.session.labelling != Labelling.ONE_TWO_THREE
        result: DispatchResult = self.session.dispatch(ApplyCmd(name))
        # Apply streams multiple "step N: from -> to" lines; the board
        # animation already shows what happened, so summarise to a count.
        step_lines: list[str] = [
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
        recipe: Recipe | None = self.session.registry.get(name)
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
        prev: wx.Dialog | None = getattr(self, "_rebinding_dlg", None)
        if prev is not None:
            try:
                prev.Destroy()
            except RuntimeError:
                pass
            self._rebinding_dlg = None

        labelling: Labelling = self.session.labelling
        left_items: list[str] = [
            f"{i}: {a} → {b}" for i, (a, b) in enumerate(moves, 1)
        ]
        right_items: list[str] = [
            f"{i}: {fp} → {tp}"
            for i, (fp, tp) in enumerate(rebound_moves(moves, labelling), 1)
        ]
        key: list[str] = [
            f"label {label} → peg {peg}" for label, peg in rebinding(labelling)
        ]

        # Layout (the three panels + Close) is RebindingDialog in hanoi.xrc;
        # here we only fetch the named controls and fill in the dynamic bits:
        # title, intro, the left header text, the key, the two lists, fonts,
        # the scroll-sync, and Close.
        dlg: wx.Dialog = self._load_hanoi_xrc().LoadDialog(
            self, "RebindingDialog"
        )
        dlg.SetTitle(title)
        mono: wx.Font = wx.Font(
            12,
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )
        xrcctrl = wx.xrc.XRCCTRL
        xrcctrl(dlg, "rebind_intro").SetLabel(intro)
        xrcctrl(dlg, "rebind_left_header").SetLabel(left_header)
        key_text: wx.StaticText = xrcctrl(dlg, "rebind_key")
        key_text.SetLabel("\n".join(key))
        key_text.SetFont(mono)

        left_lb: wx.ListBox = xrcctrl(dlg, "rebind_left")
        right_lb: wx.ListBox = xrcctrl(dlg, "rebind_right")
        listbox: wx.ListBox
        items: list[str]
        for listbox, items in ((left_lb, left_items), (right_lb, right_items)):
            listbox.SetFont(mono)
            listbox.Set(items)
            row_h: int = max(1, listbox.GetCharHeight())
            listbox.SetMinSize((210, row_h * 10 + 8))

        # Selecting a move selects the matching one on the other side AND
        # scrolls both so they line up. Both lists have the same number of
        # rows, so pinning the same first item aligns them. (Programmatic
        # SetSelection does not fire EVT_LISTBOX, so there's no feedback loop.)
        def _sync(
            src: wx.ListBox, dst: wx.ListBox
        ) -> Callable[[wx.CommandEvent], None]:
            """Build the selection handler that mirrors `src` onto `dst`."""

            def handler(_evt: wx.CommandEvent) -> None:
                """Select and scroll `dst` to match `src`'s selection."""
                i: int = src.GetSelection()
                if i == wx.NOT_FOUND:
                    return
                lb: wx.ListBox
                for lb in (src, dst):
                    if i >= lb.GetCount():
                        continue
                    lb.SetSelection(i)
                    # Scroll BOTH lists to put row i in the same place, so the
                    # matched moves line up visually. SetFirstItem pins the top
                    # row; not every wx port exposes it, so fall back to
                    # EnsureVisible. getattr avoids crashing if a method is
                    # absent — verify wx calls, don't assume (sizer lesson).
                    set_first: Callable[[int], object] | None = getattr(
                        lb, "SetFirstItem", None
                    )
                    if set_first is not None:
                        set_first(i)
                    else:
                        ensure: Callable[[int], object] | None = getattr(
                            lb, "EnsureVisible", None
                        )
                        if ensure is not None:
                            ensure(i)

            return handler

        left_lb.Bind(wx.EVT_LISTBOX, _sync(left_lb, right_lb))
        right_lb.Bind(wx.EVT_LISTBOX, _sync(right_lb, left_lb))

        def _close(_evt: wx.Event) -> None:
            """Forget and destroy the reusable rebinding dialog."""
            self._rebinding_dlg = None
            dlg.Destroy()

        dlg.Bind(wx.EVT_BUTTON, _close, id=wx.ID_CLOSE)
        dlg.Bind(wx.EVT_CLOSE, _close)
        dlg.Fit()
        dlg.Show()
        self._rebinding_dlg = dlg

    def _view_recipe(self, name: str) -> None:
        """Show a saved recipe (Recipe menu → <name> → View): the three-panel
        rebinding view when the pegs are relabelled (the method's showpiece —
        recipe moves, the label→peg key, the rebound moves), else the plain
        step list."""
        recipe: Recipe | None = self.session.registry.get(name)
        relabelled: bool = self.session.labelling != Labelling.ONE_TWO_THREE
        if relabelled and recipe is not None:
            self._show_rebinding_dialog(
                title=f"Recipe '{name}' — rebinding",
                intro=(
                    "This recipe is written in labels 1, 2, 3. Under your "
                    "relabelling,\neach move rebinds to a physical peg — the "
                    "same solution, new labels."
                ),
                left_header="Recipe moves",
                moves=recipe.default_moves,
            )
            return
        result: DispatchResult = self.session.dispatch(ShowCmd(name))
        self._show_recipe_dialog(f"Recipe '{name}'", result.lines)

    def _rebuild_recipe_menu(self) -> None:
        """Rebuild the Recipe menu's tail: one submenu per saved recipe (each
        'View' / 'Apply'), or a disabled placeholder when none are saved. The
        head (Save + separator, indices 0-1) is kept; everything after it is
        deleted and re-appended. Called whenever the saved set changes, so the
        menu mirrors the registry — point-at-the-object instead of a chooser."""
        items: list[wx.MenuItem] = list(self._recipe_menu.GetMenuItems())
        stale: wx.MenuItem
        for stale in items[2:]:
            self._recipe_menu.Delete(stale)
        names: list[str] = self.registry.names()
        if not names:
            empty: wx.MenuItem = self._recipe_menu.Append(
                wx.ID_ANY, "(no saved recipes yet)"
            )
            empty.Enable(False)
            self._recipe_menu_names = []
            return
        name: str
        for name in names:
            recipe: Recipe | None = self.registry.get(name)
            assert recipe is not None  # name came from registry.names()
            submenu: wx.Menu = wx.Menu()
            view_item: wx.MenuItem = submenu.Append(
                wx.ID_ANY, "&View", "Show this recipe's steps"
            )
            apply_item: wx.MenuItem = submenu.Append(
                wx.ID_ANY, "&Apply", "Replay under the current labelling"
            )
            self._recipe_menu.AppendSubMenu(
                submenu,
                f"{name}  ({recipe.disk_count} discs, "
                f"{len(recipe.default_moves)} moves)",
            )
            self.Bind(
                wx.EVT_MENU,
                lambda _e, n=name: self._view_recipe(n),
                id=view_item.GetId(),
            )
            self.Bind(
                wx.EVT_MENU,
                lambda _e, n=name: self._apply_recipe_by_name(n),
                id=apply_item.GetId(),
            )
        self._recipe_menu_names = list(names)

    def _show_recipe_dialog(self, title: str, lines: list[str]) -> None:
        """Scrollable list of lines (a recipe's steps, or the recipe list) in
        the RecipeDialog layout from hanoi.xrc. Non-modal so the user can keep
        playing (or open a second recipe to compare) while it's on screen; a
        `wx.MessageBox` chokes on the multi-hundred-step recipes a large game
        can produce."""
        dlg: wx.Dialog = self._load_hanoi_xrc().LoadDialog(self, "RecipeDialog")
        dlg.SetTitle(title)
        listbox: wx.ListBox = wx.xrc.XRCCTRL(dlg, "recipe_steps")
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
        row_h: int = max(1, listbox.GetCharHeight())
        listbox.SetMinSize((360, row_h * 10 + 8))

        dlg.Bind(wx.EVT_BUTTON, lambda _e: dlg.Destroy(), id=wx.ID_CLOSE)
        dlg.Bind(wx.EVT_CLOSE, lambda _e: dlg.Destroy())
        dlg.Fit()
        dlg.Show()

    def _on_toggle_history(self, _evt: wx.CommandEvent) -> None:
        """Show or hide the always-visible move-history panel (View menu)."""
        if self._history_panel is not None:
            self._history_panel.Show(self._history_toggle.IsChecked())
            self.Layout()

    def _show_howto(self, show: bool) -> None:
        """Show or hide the How-to-Play panel, keeping the panel, the View
        check item, and the frame layout in sync."""
        if self._howto_panel is None:
            return
        self._howto_panel.Show(show)
        self._howto_toggle.Check(show)
        self.Layout()

    def _on_toggle_howto(self, _evt: wx.CommandEvent) -> None:
        """View → How to play: show/hide the panel per the check item."""
        self._show_howto(self._howto_toggle.IsChecked())

    def _on_help_howto(self, _evt: wx.CommandEvent) -> None:
        """Help → How to Play: reopen the onboarding panel at any time."""
        self._show_howto(True)

    def _dismiss_howto(self) -> None:
        """Close the panel from its 'Got it' button."""
        self._show_howto(False)

    def _on_howto_dont_show(self, evt: wx.CommandEvent) -> None:
        """Persist the 'Don't show this again' choice for the next launch
        (the panel stays open now; 'Got it' closes it)."""
        self._config.WriteBool(CONFIG_SHOW_HOWTO, not evt.IsChecked())
        self._config.Flush()

    def _update_history(self) -> None:
        """Repopulate the always-visible move-history panel from the recorder.

        Every move this game (typed or applied) in the default 1-2-3 (physical)
        labels, with a live count vs the optimal 2^N-1; resets with a new game
        (the recorder's lifetime). Called from `_refresh`, so it tracks every
        command.
        """
        if self._history_list is None or self._history_header is None:
            return
        moves: list[tuple[int, int]] = list(self.session.recorder.default_moves)
        self._history_list.Set(format_move_tally(moves))
        count: int = len(moves)
        noun: str = "move" if count == 1 else "moves"
        self._history_header.SetLabel(
            f"{count} {noun} · optimal {self.session.min_moves()} "
            "(default 1-2-3 labels)"
        )

    def _update_goal(self) -> None:
        """Set the persistent goal line in the status bar (field 0) for the
        current disc count. The full rules live in the How-to-Play panel, so
        this stays terse."""
        self.SetStatusText(
            f"Goal: move all {self.session.num_disks} discs to peg 3", 0
        )

    # --- State helpers ---------------------------------------------------

    def _new_game(self, n: int) -> None:
        """Start a fresh `n`-disc game (keep the registry) and refresh."""
        self.session = GameSession(num_disks=n, registry=self.registry)
        self._refresh()

    def _on_win(self) -> None:
        """Handle a win: unlock Tier 2 for the session and show the teaching
        handoff. No modal — the board stays visible; menu/button state is set
        by `_refresh` (move buttons off, Relabel + Recipe on, Save enabled)."""
        self._won_once = True
        self._refresh()  # unlock the Tier-2 menus
        min_moves: int = self.session.min_moves()
        moves: int = self.session.current_moves
        if moves == min_moves:
            verdict: str = "Optimal!"
        else:
            verdict = (
                f"{moves - min_moves} more than the minimum ({min_moves})."
            )
        self._set_status(
            f"Solved in {moves} moves — {verdict}  Relabel pegs and Recipe are "
            "now unlocked: save this solve, start a bigger stack, and reuse it."
        )

    def _on_save(self, _evt: wx.CommandEvent) -> None:
        """Prompt for a name and save the just-won solution as a recipe."""
        # Button is only enabled when won; no need to re-check.
        self._save_recipe_with_prompt()

    def _save_recipe_with_prompt(self) -> None:
        """Show the name dialog (default `solve-<n>`) and save on OK."""
        dlg: wx.TextEntryDialog
        with wx.TextEntryDialog(
            self,
            "Recipe name:",
            "Save Recipe",
            value=f"solve-{self.session.num_disks}",
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            name: str = dlg.GetValue().strip()
            if not name:
                return
            msg: str = self.session.save_recipe(name)
            self._set_status(msg)
            self._refresh()

    def _swap_renderer(self, renderer_cls: type[BoardRenderer]) -> None:
        """Tear down the current board renderer and install a new one in
        the same slot. Game state is unchanged; the new renderer gets a
        fresh `update()` so it shows the current board immediately."""
        if isinstance(self.board_renderer, renderer_cls):
            return
        sizer: wx.Sizer = self.board_slot.GetSizer()
        sizer.Clear(delete_windows=True)
        self.board_renderer = renderer_cls(self.board_slot)
        sizer.Add(self.board_renderer.widget(), proportion=1, flag=wx.EXPAND)
        self.board_slot.Layout()
        self.board_renderer.update(self.session.game, self.session.labelling)
        self._wire_board_interaction()

    def _refresh(self) -> None:
        """Redraw the board and re-sync all control state to the session.

        Updates the renderer, the move-button enable state, the moves counter,
        the active relabel-menu bullet, and the recipe list — after any command.
        """
        self.board_renderer.update(self.session.game, self.session.labelling)
        won: bool = self.session.is_won()
        self.SetStatusText(f"Moves: {self.session.current_moves}", 2)

        valid: set[tuple[int, int]] = set()
        vm: ValidMove
        for vm in self.session.game.move_options():
            f: int = (
                change_labels_on_pegs(self.session.labelling, vm.move.from_peg)
                + 1
            )
            t: int = (
                change_labels_on_pegs(self.session.labelling, vm.move.to_peg)
                + 1
            )
            valid.add((f, t))
        pair: tuple[int, int]
        btn: wx.Window
        for pair, btn in self.move_buttons.items():
            btn.Enable(not won and pair in valid)

        # Disc dragging (spike) is off once the game is won, matching the
        # move buttons.
        set_inter: Callable[[bool], None] | None = getattr(
            self.board_renderer, "set_interactive", None
        )
        if set_inter is not None:
            set_inter(not won)

        current_labels: tuple[int, ...] = tuple(
            change_labels_on_pegs(self.session.labelling, i) + 1
            for i in range(3)
        )
        # Mark the active relabel item with a leading bullet (these are normal
        # menu items, not radios — see the XRC comment; a radio's checked state
        # is unreliable on wxGTK and, worse, swallows clicks on the item it
        # thinks is already active). Rewriting the label is display-only and
        # never emits an event, so the current peg-order is always shown and
        # every click always fires.
        labels: tuple[int, int, int]
        item: wx.MenuItem
        for labels, item in self.relabel_menu_items.items():
            base: str = self.relabel_base_labels[labels]
            marker: str = "●  " if labels == current_labels else "     "
            item.SetItemLabel(marker + base)
            item.Enable(self._won_once)

        # Tier-2 gating (dim, don't remove): the Relabel and Recipe menus are
        # disabled until the first win, then stay enabled for the session.
        menubar: wx.MenuBar = self.GetMenuBar()
        if self._relabel_menu_pos >= 0:
            menubar.EnableTop(self._relabel_menu_pos, self._won_once)
        if self._recipe_menu_pos >= 0:
            menubar.EnableTop(self._recipe_menu_pos, self._won_once)
        self._recipe_save_item.Enable(won)  # can only save a won game
        # Keep the Recipe menu's per-recipe submenus in sync with the registry;
        # recipes change only on save, so rebuild only when the set differs.
        if self.registry.names() != self._recipe_menu_names:
            self._rebuild_recipe_menu()

        self._update_history()
        self._update_goal()
        self.panel.Layout()
        self.Layout()

    def _set_status(self, text: str) -> None:
        """Write `text` to the status bar's action-feedback field (field 1)."""
        self.SetStatusText(text, 1)


def main() -> None:
    app: wx.App = wx.App()
    # Names the per-user wx.Config store (the "show How-to-Play on launch"
    # preference) so it is stable across runs rather than keyed off argv[0].
    app.SetVendorName("hanoi")
    app.SetAppName("hanoi-gui")
    frame: HanoiFrame = HanoiFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
