"""Headless smoke for the wxPython learning-flow redesign + drag-drop spike.

Run it in the Python subproject's container under Xvfb (needs a display):

    cd python
    podman run --rm --entrypoint /bin/bash \
      -v "$PWD":/hanoi-python:Z -v "$PWD/../ui":/ui:Z \
      -v "$PWD/../tasks/adhoc/drag-drop-spike/gui_smoke.py":/smoke.py:Z \
      hanoi-python -c 'dnf install -y xorg-x11-server-Xvfb >/dev/null 2>&1; \
                       cd /hanoi-python && xvfb-run -a python /smoke.py'

Prints "SMOKE OK <history-count>" on success. Exercises the wiring that the
format/type/test gates can't: the hidden recipe sidebar, the programmatic
Recipe/View menus, the CollapsiblePane, the Tier-2 win-unlock, the
always-visible history panel, and the board drop -> engine-dispatch path.
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

# Tier-2 now available: relabel (no dialog) then refresh.
frame._on_relabel_menu((2, 1, 3))
frame._refresh()

# View toggles and the drag interactivity switch must not raise.
frame._history_toggle.Check(False)
frame._on_toggle_history(None)
frame._howto_toggle.Check(False)
frame._on_toggle_howto(None)
frame.board_renderer.set_interactive(False)
frame.board_renderer.set_interactive(True)

assert frame._history_list is not None
print("SMOKE OK", frame._history_list.GetCount())
