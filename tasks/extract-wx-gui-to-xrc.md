# Extract more of the wx GUI into hanoi.xrc

**Status:** proposed — needs go-ahead
**Priority:** 5
**Difficulty:** 5

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
