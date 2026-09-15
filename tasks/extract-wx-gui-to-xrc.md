# Extract more of the wx GUI into hanoi.xrc

**Status:** implementation complete (2026-09-15) — **menu bar AND both dialogs extracted to XRC**
(menu bar confirmed working by the maintainer). About stays a stock `wx.MessageBox` (not XRC-able,
correctly left). **Awaiting a human GUI verify of the two dialogs**; archivable after that + commit.
**Priority:** 5
**Difficulty:** 5

## Progress (2026-09-15)

**Menu bar → XRC — done.** The whole `wxMenuBar` (Game / Relabel pegs / View→Board Style / Help,
including accelerators and the two radio groups) now lives in `hanoi.xrc` as `main_menubar`;
`_build_menu_bar` in `hanoigui.py` shrank from hand-building every menu/item to: load once
(`_load_hanoi_xrc`, a new guarded one-time loader shared with the panel load), `LoadMenuBar(
"main_menubar")`, bind each item by `XRCID(name)`, and `FindItemById` the radio MenuItems `_refresh`
toggles. New/Quit/About use stock names (`wxID_NEW`/`wxID_EXIT`/`wxID_ABOUT`) to keep stock-id
behaviour; relabel + board-style are `<radio>` groups. The relabel status-bar feedback and the
`IsChecked` guard (the "relabel won't stick" fix) are preserved. **Verified here:** XRC is valid XML
with all objects present, `hanoigui.py` compiles, ruff clean, 124 tests pass. **NOT verified:** actual
rendering/behaviour (no wxPython in the agent sandbox) — needs `hanoi-gui` run.

**Human check before continuing:** run `hanoi-gui` and confirm every menu still works — Game
New/New-same/Quit, all six **Relabel pegs** radios (and that the active one stays checked), View →
Board Style Text/Graphics, Help → About, plus the Ctrl+N / Ctrl+Q accelerators. If good, the dialogs
are next (below); if a menu misbehaves, the XRC/bind pattern needs adjusting before reusing it.

**Dialogs → XRC — done (2026-09-15).** Both real dialogs now load from `hanoi.xrc`:
- `RecipeDialog` (recipe-show) — a `wxListBox` + Close; `_show_recipe_dialog` does `LoadDialog` +
  `XRCCTRL("recipe_steps")`, sets the mono font / items / min-size in Python, binds Close, `Fit`.
- `RebindingDialog` (the three-panel view) — intro + [left list | centred key | right list] + Close,
  with bold headings styled in XRC. `_show_rebinding_dialog` fetches the named controls
  (`rebind_intro`, `rebind_left_header`, `rebind_key`, `rebind_left`, `rebind_right`), fills in the
  dynamic title/intro/header/key/items + mono fonts, and keeps the **scroll-sync** and the
  **reusable-single-window** logic in Python. The `_list_panel` helper and all hand-built sizers are
  gone. The `wxALIGN_CENTER_VERTICAL` gotcha is avoided (middle key uses `wxALIGN_CENTER_HORIZONTAL`
  + stretch spacers, in XRC now).
- **About** stays `wx.MessageBox` — a stock dialog, nothing to move.

Net: `hanoigui.py` no longer hand-builds any menu or dialog layout; `hanoi.xrc` holds the panel, the
menu bar, and both dialogs. **Verified here:** XRC valid (40 named objects), compiles, ruff clean,
124 tests pass. **NOT verified:** dialog rendering/behaviour — needs a `hanoi-gui` run: open a recipe
(Show / double-click) and trigger the rebinding view (apply or a move under a relabelling), and check
the three panels render, the scroll-sync works, Close works, and repeated moves reuse one window.

**Remaining:** just the human GUI verify of the two dialogs. Then archive.

## BLUF

Move as much of the wx GUI's UI *structure* as practical out of Python and into the XRC resource
(`python/src/hanoigame/hanoi.xrc`), leaving only event bindings, fonts, and dynamic content in
`hanoigui.py`. The main panel is already XRC; the **menubar and all the dialogs are still built
inline in Python** — those are the extraction targets. Use modelviewprojection's `wxapp2.py` +
`wxapp2.xrc` as the worked reference. "Done" = the menubar (and the feasible dialog layouts) load
from XRC via `XmlResource`, the GUI behaves identically, and `hanoigui.py` shrinks to logic +
bindings.

## Context — read first

- **Already in XRC** (`hanoi.xrc`, ~207 lines): `HanoiPanel` — the board slot (`board_slot`), the
  recipe list (`recipe_list`), the recipe buttons (`recipe_save`/`recipe_apply`/`recipe_show`), and
  the six move buttons (`move_1_2` … `move_3_2`). `hanoigui.py` loads it with
  `wx.xrc.XmlResource.Get().Load(...)` + `LoadPanel(self, "HanoiPanel")`, then fetches controls via
  `XRCCTRL` and binds events by `XRCID`. This is the pattern to extend.
- **Still built inline in `hanoigui.py`** (the work):
  - **The menubar** — `Game` (New / New-same / Quit), **`Relabel pegs`** (six `AppendRadioItem`),
    `View → Board Style` (Text/Graphics radio), `Help → About`. All hand-built with `wx.Menu()` /
    `AppendRadioItem` / `self.Bind(wx.EVT_MENU, …, item)`. XRC supports `wxMenuBar`/`wxMenu`/menu
    items with `radio` — extract the whole bar and `LoadMenuBar`/`SetMenuBar`, then bind by `XRCID`.
  - **Dialogs** — the three-panel **rebinding dialog** (`_show_rebinding_dialog`), the **recipe-show**
    list dialog (`_show_recipe_dialog`), and the About box. Their *layout* (panels, list boxes,
    static text, buttons) can move to XRC (`wxDialog` + `LoadDialog` + `XRCCTRL` to populate); the
    **dynamic content stays in Python** (the recipe/move rows, the label→peg key, the synced-scroll
    selection handlers). Extract the skeleton, keep the behaviour.
- **Reference:** `modelviewprojection` (`github.com/billsix/modelviewprojection`) —
  `src/modelviewprojection/wxapp2.py` + `wxapp2.xrc` show the XRC-driven idiom (menus/dialogs in XRC,
  logic in Python). `wxapp.py` is the non-XRC variant for contrast.
- **Keep in Python (do NOT move to XRC):** event bindings, `wx.Font` setup, the board renderer swap,
  the rebinding dialog's data population + scroll-sync, and the two wx/GTK gotchas already recorded in
  `tasks/reference/architecture-overview.md` (sizer alignment flags; don't re-`Check` the active radio
  item — a regression here would reintroduce the "relabel won't stick" bug).

## Plan

- [ ] Read `hanoi.xrc`, `hanoigui.py`, and mvp's `wxapp2.xrc`/`wxapp2.py`.
- [ ] Extract the **menubar** into `hanoi.xrc`; load it (`LoadMenuBar` or an XRC `wxMenuBar` object),
      rebind each item by `XRCID` (radio items included). Preserve the relabel handler's status-bar
      feedback and the `IsChecked` guard.
- [ ] Extract the **dialog layouts** that are static enough (recipe-show list; the rebinding dialog's
      three-panel skeleton; About) into XRC; populate/behaviour-bind in Python via `XRCCTRL`.
- [ ] Leave anything genuinely dynamic or awkward in Python and say why (XRC is for structure).
- [ ] Verify: **human run** of `hanoi-gui` — menus (esp. Relabel + Text/Graphics), recipe
      save/apply/show, and the rebinding dialog all still work. (wxPython isn't importable in the
      agent sandbox, so the agent can only `py_compile` + reason; a human must confirm rendering.)

## Notes

- Net effect should be *less* Python UI-construction code and a single declarative source of layout,
  matching how `HanoiPanel` already works — easier to tweak the GUI without touching code.

## Related

- `python/src/hanoigame/hanoi.xrc`, `python/src/hanoigame/hanoigui.py`.
- `modelviewprojection` `src/modelviewprojection/wxapp2.py` + `wxapp2.xrc`.
- `tasks/reference/architecture-overview.md` — frontends + the wx/GTK gotchas to preserve.
