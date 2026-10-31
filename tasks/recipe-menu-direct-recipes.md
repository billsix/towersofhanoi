# Recipe menu: saved recipes as objects (submenu → View / Apply)

**Status:** wxPython implementation DONE 2026-10-31 (staged, maintainer commits); the fan-out to the
other front-ends is tracked by `tasks/fan-out-ui-learning-flow.md`. Archive after the work commit
exists (owed, own commit). On-display `cd python && make wx` (win a game, Save, then open the Recipe
menu) is the maintainer's last check.
**Priority:** 4
**Difficulty:** 3

## BLUF

Restructure the Tier-3 Recipe menu so the user **points at the recipe itself**: "Save Current
Solution" (Ctrl+S) is the fixed first item (dimmed until the first win), and below a separator each
**saved recipe is a submenu that expands to View / Apply**. The abstract verb items ("Apply Recipe…",
"Show Recipe…", "List Recipes…"), each of which popped a chooser dialog, are gone. More HIG-aligned —
see-and-point, recognition over recall, fewer modal choosers. Done (wxPython) = the menu lists the
registry's recipes live; the fan-out carries the shape to the other front-ends.

## Context (cold-start orientation)

- **Supersedes** the programmatic Recipe menu built in the learning-flow redesign
  (`tasks/archive/2026/10/31/ui-learning-flow-spec-and-wxpython.md`), which had Save + Apply…/Show…/
  List… items. Ruling #2 of `tasks/reference/ui-design-principles.md` ("recipes live in Tier 3 — a
  menu in a GUI") is unchanged; this settles the menu's *internal* shape.
- **HIG rationale (maintainer's proposal, 2026-10-31):** listing the actual saved recipes as menu
  items, each hover-expanding to View/Apply, lets the learner act on the object instead of invoking a
  verb that then asks "which one?" (the `wx.SingleChoiceDialog` indirection). It removes two redundant
  modes ("List" is redundant once the menu *is* the list; the Show/Apply choosers vanish).

## Decisions (maintainer, 2026-10-31 — delegated "whatever you recommend")

- **Save = the Recipe menu's first item, `Ctrl+S`, dimmed until the first win** — *not* a floating
  workspace button (a button would sit disabled most of the time, the "chrome you can't use" the
  status-bar goal-line change just removed; the win handoff status message already nudges toward it).
- **View** opens the three-panel **rebinding view** when the pegs are relabelled (the method's
  showpiece: recipe moves | label→peg key | rebound moves), else the plain step list.
- **Empty / gated:** a disabled "(no saved recipes yet)" placeholder when none are saved; the whole
  menu stays dimmed (Tier-2 gating) until the first win.

## Work record (wxPython, 2026-10-31)

- `python/src/hanoigame/hanoigui.py`: the Recipe menu keeps a fixed head (Save + separator); new
  `_rebuild_recipe_menu` deletes everything after index 1 and re-appends one `AppendSubMenu` per saved
  recipe ("name (D discs, M moves)") with **View** / **Apply** items, or the disabled placeholder.
  `_refresh` calls it only when `registry.names()` differs from the cached `_recipe_menu_names` (saves
  are the only change). New `_view_recipe(name)`; `_apply_recipe_by_name` reused for Apply. Removed
  `_on_apply_recipe`, `_on_show_recipe`, `_on_list_recipes`, `_choose_recipe`, `_recipe_display_lines`
  (the chooser-dialog path, incl. the only `wx.SingleChoiceDialog`).
- Verification: `make format` / `type-check` / `test` green (130 passed / 2 skipped); the headless
  smoke (`python/tools/gui_smoke.py`) now saves a recipe and asserts it appears in `_recipe_menu_names`.
  A `wx.MenuItemList` isn't sliceable — wrap in `list()` before `[2:]` (fixed).

## Related

- `tasks/reference/ui-design-principles.md` (ruling #2 recipes in Tier 3; see-and-point, recognition
  over recall), `tasks/reference/feature-spec.md` §4.8 (recipe apply + rebinding), §6.2 (GUI recipe
  presentation), §3.5 (tiers).
- `tasks/fan-out-ui-learning-flow.md` — carries this menu shape to the other front-ends (Tier 3).
- `tasks/how-to-play-welcome-screen.md` — the sibling onboarding refinement done the same day.
