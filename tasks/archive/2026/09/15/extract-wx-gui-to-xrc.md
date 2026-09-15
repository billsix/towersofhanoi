# Extract more of the wx GUI into hanoi.xrc

**Status:** complete (2026-09-15) — menu bar and both dialogs extracted to XRC; all verified in the
GUI by the maintainer (menus, the recipe-steps list via Show Selected, and the rebinding three-panel
view via apply/move under a relabelling all render and behave correctly).
**Priority:** 5
**Difficulty:** 5

## BLUF

Moved the wx GUI's remaining UI *structure* out of Python and into the XRC resource
(`python/src/hanoigame/hanoi.xrc`), leaving only event bindings, fonts, and dynamic content in
`hanoigui.py`. At the start only `HanoiPanel` was in XRC; the menu bar and every dialog were hand-built
inline. Both were extracted, so `hanoigui.py` no longer constructs any menu or dialog layout.
modelviewprojection's `wxapp2.py` + `wxapp2.xrc` (`github.com/billsix/modelviewprojection`) were the
worked reference for the XRC-driven idiom.

## What was done

**Menu bar → XRC.** The whole `wxMenuBar` (Game / Relabel pegs / View→Board Style / Help, with
accelerators and the radio groups) moved into `hanoi.xrc` as `main_menubar`. `_build_menu_bar` shrank
from hand-building every menu and item to: load the XRC once (`_load_hanoi_xrc`, a guarded one-time
loader shared with the panel load), `LoadMenuBar("main_menubar")`, bind each item by `XRCID(name)`, and
`FindItemById` the items `_refresh` updates. New/Quit/About kept stock ids (`wxID_NEW`/`wxID_EXIT`/
`wxID_ABOUT`) to preserve stock-id behaviour. (The relabel group was `<radio>` items at this point, with
the then-current `IsChecked` guard; that radio approach was replaced by normal menu items shortly after
in `fix-relabel-radio-desync-gtk` — see Related — because wxGTK swallows clicks on an already-active
radio. This task carried the relabel handling across unchanged; the replacement was separate work.)

**Dialogs → XRC.** Both real dialogs now load from `hanoi.xrc`:
- `RecipeDialog` (recipe-show) — a `wxListBox` + Close. `_show_recipe_dialog` does `LoadDialog` +
  `XRCCTRL("recipe_steps")`, then sets the mono font / items / min-size in Python, binds Close, `Fit`.
- `RebindingDialog` (the three-panel view) — intro + [left list | centred key | right list] + Close,
  bold headings styled in XRC. `_show_rebinding_dialog` fetches the named controls (`rebind_intro`,
  `rebind_left_header`, `rebind_key`, `rebind_left`, `rebind_right`), fills in the dynamic
  title/intro/header/key/items and mono fonts, and keeps the scroll-sync and the reusable-single-window
  logic in Python. The old `_list_panel` helper and all hand-built sizers were removed. The
  `wxALIGN_CENTER_VERTICAL`-in-a-vertical-sizer gotcha was avoided (the middle key uses
  `wxALIGN_CENTER_HORIZONTAL` + stretch spacers, now expressed in XRC).
- **About** stayed a stock `wx.MessageBox` — nothing to move.

Net: `hanoigui.py` builds no menu or dialog layout; `hanoi.xrc` holds the panel, the menu bar, and both
dialogs — a single declarative source of layout, matching how `HanoiPanel` already worked.

## Verification

In the agent sandbox (no wxPython): XRC valid XML with all objects present, `hanoigui.py` compiled, ruff
clean, 124 tests passed. Rendering/behaviour could only be confirmed by a human `hanoi-gui` run: the
maintainer verified the menus, the recipe-steps list (Show Selected / double-click), and the rebinding
three-panel view (three panels render, scroll-sync works, Close works, repeated moves reuse one window).

## Decisions worth keeping

- Kept in Python (not XRC), deliberately: event bindings, `wx.Font` setup, the board-renderer swap, and
  every dialog's dynamic data population + scroll-sync. XRC describes static structure only.
- The wx/GTK gotchas encountered here (sizer alignment flags; and, in the follow-on, why relabel must
  use normal menu items) live in `tasks/reference/architecture-overview.md`, which is the durable home.

## Related

- `python/src/hanoigame/hanoi.xrc`, `python/src/hanoigame/hanoigui.py`.
- `modelviewprojection` `src/modelviewprojection/wxapp2.py` + `wxapp2.xrc` — the XRC-driven reference.
- `tasks/reference/architecture-overview.md` — frontends + the wx/GTK gotchas.
- `tasks/archive/2026/09/15/fix-relabel-radio-desync-gtk.md` — the follow-on that replaced the relabel
  radio group with normal menu items.
