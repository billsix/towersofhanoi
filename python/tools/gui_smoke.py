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
always-visible history panel, the status-bar goal line, and the board drop ->
engine-dispatch path. (How-to-Play is a centered modal dialog now and is not
exercised here -- ShowModal would block this no-loop harness.)
"""

import wx

from hanoigame.board_renderers import GraphicsBoardRenderer
from hanoigame.hanoigui import HanoiFrame

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

# The View history toggle and the drag interactivity switch must not raise.
frame._history_toggle.Check(False)
frame._on_toggle_history(None)
frame.board_renderer.set_interactive(False)
frame.board_renderer.set_interactive(True)

# How-to-Play is now a centered MODAL dialog (shown on first run + from
# Help -> How to Play). ShowModal would block this no-loop harness, so it is not
# exercised here -- the maintainer's on-display run is the check.

# Goal line now lives in status-bar field 0.
assert "Goal: move all" in frame.GetStatusBar().GetStatusText(0)

assert frame._history_list is not None
print("SMOKE OK", frame._history_list.GetCount())
