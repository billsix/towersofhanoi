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

"""Board renderers for the wxPython front-end.

Two strategies behind a common interface:

- TextBoardRenderer wraps the original wx.TextCtrl rendering, using
  `presenter.render()` so the GUI's text view stays in lock-step with
  CLI and curses output.
- GraphicsBoardRenderer paints the board directly with
  wx.GraphicsContext — rounded-rect pegs and gradient discs, antialiased,
  no SVG assets.

A future renderer (OpenGL is the next planned subclass) just implements
`widget()` + `update()`; the frame's `_swap_renderer()` handles the
rest.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

import wx

from . import presenter
from .hanoimodel import HanoiGame
from .presenter import Labelling, change_labels_on_pegs


class BoardRenderer(ABC):
    """Strategy interface. HanoiFrame owns one renderer at a time and
    swaps subclasses via View → Board Style."""

    @abstractmethod
    def widget(self) -> wx.Window:
        """The wx.Window to insert into the layout slot. Owned by the
        renderer; destroyed when the renderer is discarded."""

    @abstractmethod
    def update(self, game: HanoiGame, labelling: Labelling) -> None:
        """Re-render after game state or labelling changes."""


class TextBoardRenderer(BoardRenderer):
    """ASCII view via wx.TextCtrl + presenter.render. Identical output to
    CLI and curses; the only frontend-shared option."""

    def __init__(self, parent: wx.Window) -> None:
        self._text = wx.TextCtrl(
            parent,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL,
        )
        self._text.SetFont(
            wx.Font(
                12,
                wx.FONTFAMILY_TELETYPE,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        self._text.Bind(wx.EVT_SIZE, self._on_size)
        self._game: Optional[HanoiGame] = None
        self._labelling: Optional[Labelling] = None

    def widget(self) -> wx.Window:
        return self._text

    def update(self, game: HanoiGame, labelling: Labelling) -> None:
        self._game = game
        self._labelling = labelling
        self._redraw()

    def _on_size(self, evt) -> None:
        evt.Skip()
        if self._game is not None:
            self._redraw()

    def _redraw(self) -> None:
        lines = presenter.render(self._game, self._labelling)
        if not lines:
            self._text.SetValue("")
            return
        panel_w_px, panel_h_px = self._text.GetSize()
        char_w = max(1, self._text.GetCharWidth())
        line_h = max(1, self._text.GetCharHeight())
        visible_cols = max(1, panel_w_px // char_w)
        visible_rows = max(1, panel_h_px // line_h)
        line_width = len(lines[0])
        h_pad = max(0, (visible_cols - line_width) // 2)
        centred = [(" " * h_pad + line) for line in lines]
        # -1 of slack so the bottom line isn't sitting under the scrollbar.
        v_pad = max(0, visible_rows - len(centred) - 1)
        self._text.SetValue("\n" * v_pad + "\n".join(centred))


# Label badge colours (the small numbered circles below each peg) follow
# the *label* — blue/yellow/red, matching the curses palette. Discs do
# NOT follow the label; see `_DISC_COLOURS` below.
_LABEL_COLOURS: List[wx.Colour] = [
    wx.Colour(70, 130, 200),
    wx.Colour(230, 195, 70),
    wx.Colour(220, 90, 80),
]

# Disc colour follows disc *size* (identity), not the peg it sits on, so
# moving a disc never changes its appearance. Ten colours so a 10-disc
# game stays readable; cycles harmlessly past that.
_DISC_COLOURS: List[wx.Colour] = [
    wx.Colour(232, 80, 80),
    wx.Colour(232, 145, 70),
    wx.Colour(235, 200, 75),
    wx.Colour(170, 210, 80),
    wx.Colour(85, 195, 130),
    wx.Colour(75, 170, 220),
    wx.Colour(100, 130, 220),
    wx.Colour(160, 110, 220),
    wx.Colour(220, 110, 200),
    wx.Colour(185, 145, 110),
]

_REFERENCE_LABEL_COLOUR = wx.Colour(170, 178, 195)

_BG_TOP = wx.Colour(45, 52, 68)
_BG_BOTTOM = wx.Colour(20, 26, 38)
_PEG_LIGHT = wx.Colour(200, 162, 110)
_PEG_DARK = wx.Colour(120, 86, 50)
_BASE_FILL = wx.Colour(150, 110, 70)
_BASE_EDGE = wx.Colour(90, 64, 38)
_SHADOW = wx.Colour(0, 0, 0, 90)


class GraphicsBoardRenderer(BoardRenderer):
    """Procedurally-drawn 2D board. wx.Panel + EVT_PAINT + GraphicsContext;
    no SVG assets — discs and pegs are rounded rectangles with linear
    gradients, plus a manual shadow per disc."""

    def __init__(self, parent: wx.Window) -> None:
        self._panel = wx.Panel(parent)
        self._panel.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self._panel.Bind(wx.EVT_PAINT, self._on_paint)
        self._panel.Bind(wx.EVT_SIZE, self._on_size)
        self._game: Optional[HanoiGame] = None
        self._labelling: Optional[Labelling] = None

    def widget(self) -> wx.Window:
        return self._panel

    def update(self, game: HanoiGame, labelling: Labelling) -> None:
        self._game = game
        self._labelling = labelling
        self._panel.Refresh()

    def _on_size(self, _evt) -> None:
        self._panel.Refresh()

    def _on_paint(self, _evt) -> None:
        dc = wx.AutoBufferedPaintDC(self._panel)
        gc = wx.GraphicsContext.Create(dc)
        if not gc:
            # Fall back to a flat background if GC creation fails.
            dc.SetBackground(wx.Brush(_BG_BOTTOM))
            dc.Clear()
            return
        self._paint_background(gc)
        if self._game is not None and self._game.num_disks > 0:
            self._paint_game(gc)

    # --- Painting ------------------------------------------------------

    def _paint_background(self, gc: wx.GraphicsContext) -> None:
        w, h = self._panel.GetSize()
        bg = gc.CreateLinearGradientBrush(0, 0, 0, h, _BG_TOP, _BG_BOTTOM)
        gc.SetBrush(bg)
        gc.SetPen(wx.TRANSPARENT_PEN)
        path = gc.CreatePath()
        path.AddRectangle(0, 0, w, h)
        gc.DrawPath(path)

    def _paint_game(self, gc: wx.GraphicsContext) -> None:
        n = self._game.num_disks
        w, h = self._panel.GetSize()

        # When the user has relabelled, add a small default-1-2-3
        # reference row below the active labelling — same affordance the
        # text presenter uses (default_label_row).
        has_reference = self._labelling != Labelling.ONE_TWO_THREE

        margin = 20
        label_band_h = 60 if has_reference else 36
        base_h = 14

        avail_w = max(80, w - 2 * margin)
        avail_h = max(80, h - 2 * margin - label_band_h - base_h)
        peg_zone_w = avail_w / 3

        disc_h = min(avail_h / max(n, 4) * 0.92, 30)
        max_disc_w = peg_zone_w * 0.92
        peg_w = max(8, max_disc_w * 0.07)
        peg_h = avail_h * 0.95

        base_y = h - margin - label_band_h - base_h
        peg_top_y = base_y - peg_h

        peg_centres = [margin + peg_zone_w * (i + 0.5) for i in range(3)]

        # Base bar across the full width.
        self._draw_rounded_fill(
            gc,
            margin,
            base_y,
            w - 2 * margin,
            base_h,
            _BASE_FILL,
            _BASE_EDGE,
            radius=4,
        )

        # Pegs — vertical rounded rects with a left-to-right gradient so
        # they read as cylinders.
        for cx in peg_centres:
            peg_brush = gc.CreateLinearGradientBrush(
                cx - peg_w / 2,
                0,
                cx + peg_w / 2,
                0,
                _PEG_DARK,
                _PEG_LIGHT,
            )
            gc.SetBrush(peg_brush)
            gc.SetPen(wx.Pen(_PEG_DARK, 1))
            path = gc.CreatePath()
            path.AddRoundedRectangle(
                cx - peg_w / 2, peg_top_y, peg_w, peg_h, peg_w / 2
            )
            gc.DrawPath(path)

        # Discs — drawn bottom-up so shadows from upper discs sit on
        # top of the disc beneath them. Colour is by disc *size* so a
        # disc keeps its identity as it moves between pegs.
        for p_idx, peg in enumerate(self._game.towers):
            cx = peg_centres[p_idx]
            for stack_idx, size in enumerate(peg):
                disc_w = self._disc_width(size, n, max_disc_w)
                y = base_y - (stack_idx + 1) * disc_h * 1.04
                self._draw_disc(
                    gc, cx, y, disc_w, disc_h, self._disc_colour(size)
                )

        # Active label badges — colour mirrors the curses peg colour for
        # this label, so the colour ↔ label binding stays legible across
        # frontends.
        active_label_y = base_y + base_h + (18 if has_reference else label_band_h / 2)
        badge_font = wx.Font(
            13,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_BOLD,
        )
        for p_idx, cx in enumerate(peg_centres):
            label = change_labels_on_pegs(self._labelling, p_idx)
            self._draw_label_badge(
                gc,
                cx,
                active_label_y,
                label + 1,
                _LABEL_COLOURS[label],
                badge_font,
            )

        # Default 1-2-3 reference row, only when the active labelling
        # differs from default. Small, neutral; just a reminder that the
        # leftmost physical peg is still "peg 1" underneath.
        if has_reference:
            ref_y = active_label_y + 26
            ref_font = wx.Font(
                10,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
            gc.SetFont(ref_font, _REFERENCE_LABEL_COLOUR)
            for p_idx, cx in enumerate(peg_centres):
                text = str(p_idx + 1)
                extents = gc.GetTextExtent(text)
                tw, th = extents[0], extents[1]
                gc.DrawText(text, cx - tw / 2, ref_y - th / 2)

    # --- Drawing helpers ----------------------------------------------

    @staticmethod
    def _disc_colour(size: int) -> wx.Colour:
        """Colour by disc size, so a disc keeps its colour as it moves."""
        return _DISC_COLOURS[(size - 1) % len(_DISC_COLOURS)]

    @staticmethod
    def _disc_width(size: int, n: int, max_w: float) -> float:
        """Linear interpolation so the smallest disc is always 1/3 the
        width of the largest — visible difference without being tiny."""
        if n <= 1:
            return max_w
        smallest = max_w / 3
        return smallest + (max_w - smallest) * (size - 1) / (n - 1)

    @staticmethod
    def _draw_rounded_fill(
        gc: wx.GraphicsContext,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: wx.Colour,
        edge: wx.Colour,
        radius: float = 4,
    ) -> None:
        gc.SetBrush(wx.Brush(fill))
        gc.SetPen(wx.Pen(edge, 1))
        path = gc.CreatePath()
        path.AddRoundedRectangle(x, y, w, h, radius)
        gc.DrawPath(path)

    def _draw_disc(
        self,
        gc: wx.GraphicsContext,
        cx: float,
        y: float,
        w: float,
        h: float,
        colour: wx.Colour,
    ) -> None:
        # Shadow first.
        gc.SetBrush(wx.Brush(_SHADOW))
        gc.SetPen(wx.TRANSPARENT_PEN)
        shadow_path = gc.CreatePath()
        shadow_path.AddRoundedRectangle(cx - w / 2 + 2, y + 4, w, h, h / 3)
        gc.DrawPath(shadow_path)

        # Vertical light-to-dark gradient: top is brighter so the disc
        # reads as a 3D cylinder lit from above.
        light = self._lighten(colour, 0.30)
        dark = self._darken(colour, 0.22)
        brush = gc.CreateLinearGradientBrush(cx, y, cx, y + h, light, dark)
        gc.SetBrush(brush)
        gc.SetPen(wx.Pen(self._darken(colour, 0.45), 1))
        path = gc.CreatePath()
        path.AddRoundedRectangle(cx - w / 2, y, w, h, h / 3)
        gc.DrawPath(path)

    def _draw_label_badge(
        self,
        gc: wx.GraphicsContext,
        cx: float,
        cy: float,
        text_num: int,
        colour: wx.Colour,
        font: wx.Font,
    ) -> None:
        r = 14
        gc.SetBrush(wx.Brush(_SHADOW))
        gc.SetPen(wx.TRANSPARENT_PEN)
        shadow_path = gc.CreatePath()
        shadow_path.AddCircle(cx + 1, cy + 2, r)
        gc.DrawPath(shadow_path)

        gc.SetBrush(wx.Brush(colour))
        gc.SetPen(wx.Pen(self._darken(colour, 0.40), 1))
        path = gc.CreatePath()
        path.AddCircle(cx, cy, r)
        gc.DrawPath(path)

        gc.SetFont(font, wx.WHITE)
        text = str(text_num)
        extents = gc.GetTextExtent(text)
        tw, th = extents[0], extents[1]
        gc.DrawText(text, cx - tw / 2, cy - th / 2)

    @staticmethod
    def _lighten(c: wx.Colour, amount: float) -> wx.Colour:
        return wx.Colour(
            int(c.Red() + (255 - c.Red()) * amount),
            int(c.Green() + (255 - c.Green()) * amount),
            int(c.Blue() + (255 - c.Blue()) * amount),
        )

    @staticmethod
    def _darken(c: wx.Colour, amount: float) -> wx.Colour:
        return wx.Colour(
            int(c.Red() * (1 - amount)),
            int(c.Green() * (1 - amount)),
            int(c.Blue() * (1 - amount)),
        )
