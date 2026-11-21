"""Headless smoke for the wxPython GUI (learning-flow tiers + drag-drop).

A manual, display-dependent check of the window wiring that the
format/type-check/test gates can't reach — NOT auto-wired into any gate (it
needs an X display; run it under Xvfb). Run it from the Python subproject:

    cd python
    podman run --rm --entrypoint /bin/bash \
      -v "$PWD":/hanoi-python:Z -v "$PWD/../ui":/ui:Z hanoi-python \
      -c 'dnf install -y xorg-x11-server-Xvfb >/dev/null 2>&1; \
          cd /hanoi-python && pip install -e . --no-index --no-deps -q; \
          xvfb-run -a python tools/gui_smoke.py'

Prints "SMOKE OK <history-count>" on success. Exercises the hidden recipe
sidebar, the programmatic Recipe/View menus, the Tier-2 win-unlock, the
always-visible history panel, the status-bar goal line, the board drop ->
engine-dispatch path, and the rebinding dialog's linked lists. Modal dialogs
(How-to-Play, the first-win teaching dialog) are stubbed to return OK at
once, since ShowModal would block this no-loop harness.
"""

import wx
import wx.xrc

from hanoigame.board_renderers import GraphicsBoardRenderer
from hanoigame.hanoigui import HanoiFrame

# This harness runs no event loop, so a modal dialog (the first-run
# How-to-Play, the first-win teaching dialog) would block it forever. Make
# every modal return OK at once; the maintainer's on-display run checks them.
wx.Dialog.ShowModal = lambda self: wx.ID_OK  # type: ignore[method-assign]
wx.MessageDialog.ShowModal = lambda self: wx.ID_OK  # type: ignore[method-assign]

app: wx.App = wx.App()
frame: HanoiFrame = HanoiFrame()

# Before any win, Tier 2 is gated.
assert not frame._won_once, "Tier 2 should start locked"

# Drag-drop plumbing: the graphics renderer exposes a wired drop callback.
assert isinstance(frame.board_renderer, GraphicsBoardRenderer)
assert frame.board_renderer._move_callback is not None, "drop callback wired"

# A board drop (physical peg 0 -> peg 1) dispatches a legal move on the fresh
# 3-disc game (top disc from peg 1 to peg 2), exactly like a move button.
before: int = len(list(frame.session.recorder.default_moves))
frame._on_board_drop(0, 1)
after: int = len(list(frame.session.recorder.default_moves))
assert after == before + 1, (before, after)

# A 1-disc game wins in one dropped move — exercises the win/unlock path.
frame._new_game(1)
frame._on_board_drop(0, 2)
assert frame._won_once, "first win should unlock Tier 2"

# A saved recipe becomes a Recipe-menu submenu (View/Apply), not a chooser.
frame.session.save_recipe("smoke")
frame._refresh()
assert "smoke" in frame._recipe_menu_names, frame._recipe_menu_names

# Tier-2 now available: relabel (no dialog) then refresh.
frame._on_relabel_menu((2, 1, 3))
frame._refresh()

# The three-panel rebinding dialog: selecting a move on the left selects the
# same row on the right and marks the two key bindings that move uses.
frame._show_rebinding_dialog(
    title="smoke",
    intro="smoke",
    left_header="Recipe moves",
    moves=[(1, 2), (1, 3), (2, 3)],
)
rebind_dlg: wx.Dialog = frame._rebinding_dlg
left_lb: wx.ListBox = wx.xrc.XRCCTRL(rebind_dlg, "rebind_left")
right_lb: wx.ListBox = wx.xrc.XRCCTRL(rebind_dlg, "rebind_right")
key_lbl: wx.StaticText = wx.xrc.XRCCTRL(rebind_dlg, "rebind_key")
left_lb.SetSelection(1)
select_evt: wx.CommandEvent = wx.CommandEvent(wx.wxEVT_LISTBOX, left_lb.GetId())
select_evt.SetEventObject(left_lb)
left_lb.GetEventHandler().ProcessEvent(select_evt)
assert right_lb.GetSelection() == 1, right_lb.GetSelection()
marked: list[str] = [
    line for line in key_lbl.GetLabel().splitlines() if line.startswith("▶")
]
assert len(marked) == 2 and "label 1" in marked[0] and "label 3" in marked[1], (
    marked
)
# Replacing the dialog (the next apply) must stop the old one's scroll timer.
frame._show_rebinding_dialog(
    title="smoke2", intro="smoke2", left_header="Recipe moves", moves=[(1, 2)]
)

# History review: clicking a history row shows the board after that move;
# a move while reviewing asks first. "No" (the stub returns OK, not YES)
# keeps the game; "Yes" deletes the later moves and makes the new move.
frame._new_game(2)
frame._on_board_drop(0, 1)  # 1. small disc 1 -> 2
frame._on_board_drop(0, 2)  # 2. big disc 1 -> 3
assert frame._history_list is not None
frame._history_list.SetSelection(0)
history_evt: wx.CommandEvent = wx.CommandEvent(
    wx.wxEVT_LISTBOX, frame._history_list.GetId()
)
frame._history_list.GetEventHandler().ProcessEvent(history_evt)
assert frame._review_count == 1, frame._review_count
assert frame._shown_game().towers == [[2], [1], []], frame._shown_game().towers
frame._on_board_drop(1, 2)  # asked; the stub answers OK (not YES): no change
assert len(frame.session.recorder.default_moves) == 2
assert frame._review_count == 1
wx.MessageDialog.ShowModal = lambda self: wx.ID_YES  # type: ignore[method-assign]
frame._on_board_drop(1, 2)  # yes: keep move 1, then small disc 2 -> 3
wx.MessageDialog.ShowModal = lambda self: wx.ID_OK  # type: ignore[method-assign]
assert frame._review_count is None
assert frame.session.recorder.default_moves == [(1, 2), (2, 3)], (
    frame.session.recorder.default_moves
)
frame._on_history_back(None)

# The View history toggle and the drag interactivity switch must not raise.
frame._history_toggle.Check(False)
frame._on_toggle_history(None)
frame.board_renderer.set_interactive(False)
frame.board_renderer.set_interactive(True)

# How-to-Play is a centered modal dialog (stubbed above).

# Goal line now lives in status-bar field 0.
assert "Goal: move all" in frame.GetStatusBar().GetStatusText(0)

assert frame._history_list is not None
print("SMOKE OK", frame._history_list.GetCount())
