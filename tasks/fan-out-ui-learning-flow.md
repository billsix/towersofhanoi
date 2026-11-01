# Fan out the learning-flow UI to every other front-end

**Status:** DONE (all front-ends merged, 2026-11-01). **Every front-end carries the three-tier
learning flow**: Python CLI/curses + Rust cli/ratatui (text), C++ ImGui, Rust egui, Rust Tauri, and
the wx trio (wxPython oracle + C++ wx + Rust wxDragon). All GUI work was on-display-verified by the
maintainer; the wx trio's two on-display fixes (a wxDragon launch segfault + dead menus) are in git
history. The shared-XRC decision (wx front-ends carry the flow in code, XRC stays structural) is
harvested into `tasks/reference/ui-design-principles.md` (ruling 6). The sibling drag-drop fan-out is
its own task (`tasks/port-drag-drop-to-graphical-uis.md`, also done). History/count/timing detail is in
the commits on the merged branches.
**Priority:** 3
**Difficulty:** 6

## Progress (2026-10-31 → 11-01)

- **Shared grammar gained a `history` command** (alias `moves`) in BOTH cores → the numbered
  default-space move tally + live count vs the optimal 2^N-1 (the text-UI form of the Tier-1
  always-visible history; feature-spec §4.11/§6.1). Python `engine._handle_history`; Rust
  `engine::handle_history` + a new `presenter::format_move_tally` mirroring Python's. **Python↔Rust
  grammar parity maintained.** ← this is a new shared primitive; flag for review before it reaches more
  UIs.
- **Python CLI (`hanoicli.py`) + Rust CLI (`hanoi-cli`) — DONE:** first-run onboarding "How to play"
  (the goal + the one rule + "solve small, relabel, replay"); an always-present **Tier-1 goal line**
  above the board (the running count is the legend's trailing `Moves: N`); **Tier-2 relabel/save stated
  in text, not hard-blocked** (§6.1 permits this for a plain terminal UI — keeps behaviour + tests).
  Tests added both languages (onboarding/goal + `history`); all gates green.
- **Python ncurses TUI (`hanoigame.py`) + Rust ratatui TUI (`hanoi`) — DONE** (branch `ui-fanout-tuis`):
  the status row now leads with the **Tier-1 goal line** (with `Moves: N/optimal` as the always-visible
  history indicator; the full numbered tally is the `history` command); the message area **opens with
  the "How to play" onboarding**, replaced by the first move's feedback; the hint lists `history`. Per
  §6.1 the always-visible history is the status count + the on-demand `history` panel (the fixed curses/
  ratatui layout makes a permanent full-tally region impractical without a larger rework). The Rust
  ratatui `screen()` render test asserts the goal line; Python/Rust gates green.
- **C++ Dear ImGui GUI (`cpp/main.cpp`) — learning-flow DONE** (branch `ui-fanout-guis`), the reference
  GUI: Tier-1 goal line + a new always-visible `draw_history` tally panel (replacing the old always-on
  recipes panel); Tier-2 `won_once` latch dims the Relabel + Recipe menus until the first win; Tier-3
  recipes moved into a **Recipe menu** (Save first, then each recipe a submenu → View/Apply, via
  `view_recipe`/`apply_recipe`); the help modal became **How to Play** (goal + the one rule + method),
  auto-opened once on first run. Builds (all targets) + ctest green; a headless Xvfb+softGL launch ran
  4 s with no ImGui assert. **On-display `make gui` is the visual check.** Drag-drop for ImGui is still
  pending (below).
- **Rust egui GUI (`rust/hanoi-egui/src/main.rs`) — learning-flow DONE** (branch `ui-fanout-egui`),
  mirroring the ImGui reference (both immediate-mode): Tier-1 goal line + an always-visible right-hand
  **History** panel (`format_move_tally` over the recorder's default-label moves, with the running count
  vs the optimal `2^N-1`) replacing the old always-on Recipes side panel; Tier-2 `won_once` latch dims
  the **Relabel** and **Recipe** menus until the first win; Tier-3 recipes and relabelling both moved
  into a top **menu bar** (`egui::menu::bar`), matching the wxPython oracle (relabel is a menu there,
  not inline controls) — Relabel menu = one radio item per permutation (active marked, dimmed while the
  current game is already solved); Recipe menu = Save current solution (enabled at a win) / Reset
  recording / separator / each saved recipe a submenu → View (`view_recipe`) / Apply
  (`apply_recipe_named`, which counts from the recipe not the suppressed step-log). Move/status text
  uses ASCII `->` (egui's default font has no `→` glyph, matching the text UIs); the first-run
  **How to Play** window (goal + the one rule + the solve-small-relabel-replay method) auto-opens once
  and reopens from a **Help** menu. The web (`#[cfg(wasm32)]`) entry is untouched — same `HanoiApp`.
  `cargo check` clean (own workspace, excluded from `make check`); a headless Xvfb + software-GL launch
  ran 6 s with no panic (EXIT=137 from `timeout -s KILL`, empty log). **On-display `make egui` is the
  visual check.** Drag-drop for egui is still pending (below).
- **Rust Tauri GUI (`rust/tauri`) — learning-flow DONE** (overnight branch), the webview front-end:
  Tier-1 goal line in the status bar + an always-visible **History** `<ol>` fed by a new `history`
  field on the backend `Snapshot` (the recorder's default-label move pairs); Tier-2 gating is a
  frontend `wonOnce` latch that disables the **Relabel** and **Recipe** menu-bar buttons until the
  first win; Tier-3 moves relabelling and recipes onto a **menu bar** (Game / Relabel / Recipe / Help)
  — Relabel menu = one radio-marked item per permutation (dimmed while solved); Recipe menu = Save
  current solution (auto-named `solve-N`, enabled at a win) + each saved recipe a row with View / Apply
  (Apply dimmed while solved); the first-run **How to Play** `<dialog>` auto-opens once and reopens from
  the Help menu. Move/history text uses ASCII `->`. The backend stays a thin view-model over the
  `hanoigame` crate (one new `history` field; no logic added). Verified: frontend `deno check`/`lint`/
  `fmt` clean (`make type-check`), backend `cargo check` clean. **On-display `make tauri` is the visual
  check.** Drag-drop for Tauri is still pending (below).
- **C++ wx (`cpp/hanoiwx.cpp`) + Rust wxDragon (`rust/hanoi-gui/src/main.rs`) — learning-flow DONE**
  (branch `ui-fanout-wx-trio`), each mirroring the wxPython oracle programmatically with the shared
  `ui/hanoi.xrc` left untouched (decision below): Tier-1 goal line (3-field status bar) + an
  always-visible move-history panel; Tier-2 `won_once` latch dimming the Relabel + Recipe menus until
  the first win; Tier-3 recipes in a **Recipe menu** (Save + per-recipe View/Apply submenus), sidebar
  gone; a first-run **How to Play** panel (goal + one rule + a legal/illegal diagram + "don't show
  again" via `wxConfig`, reopen from Help). Two **wxDragon-forced** departures (both keep the XRC
  intact): the Rust menu bar is built in code (wxDragon has no runtime menu-insert on an XRC-loaded
  `MenuBar`) and the Rust sidebar is **hidden** (not destroyed). A first cut destroyed the sidebar
  widgets, but that left the `StaticBoxSizer` holding freed pointers and GTK segfaulted in its idle
  size-allocate at launch; hiding lets wxWidgets reclaim the slot on `Layout` with nothing freed (fix
  commit `894581b`, gdb-confirmed). C++ verified via `make build` + a headless Xvfb smoke; Rust via
  `make check` + a headless Xvfb launch (ran full duration, no segfault). **Both need the maintainer's
  on-display `make wx` sign-off** (incl. whether the collapsed Rust sidebar leaves a residual gap).
  When they land, harvest the settled XRC decision into `tasks/reference/ui-design-principles.md`.
- **Tauri UX fixes folded in on this branch** (maintainer-reported on the merged Tauri GUI): the
  always-visible history `<ol>` reserved a stable scrollbar gutter (the bar had overlapped the move
  text); and the post-apply rebinding view dropped its redundant "Steps" list (the per-step replay log
  duplicated the "Recipe (its labels)" column). Only Tauri showed the duplicate — the shared engine
  already suppresses the per-step log under a relabelling (`rust/hanoigame/src/engine.rs` `handle_apply`),
  and egui/CLI/TUI reuse that. Verified: `make type-check` (deno) + Tauri backend `cargo check`.
- **Remaining:** fold in **drag-drop** per graphical UI incl. ImGui (`tasks/port-drag-drop-to-graphical-uis.md`).

## BLUF

Apply the three-tier learning-flow interface (feature-spec.md §3.5, realized in the wxPython oracle)
to every other interactive front-end, and settle the **shared `ui/hanoi.xrc` form** for the wx UIs.
Targets: Python CLI + curses TUI; Rust cli / ratatui TUI / wx (wxDragon) / Tauri / egui; C++ ImGui +
wx. Sibling of `tasks/fan-out-move-tally.md` (which this supersedes/absorbs for the GUI/TUI tally
presentation). Done = each UI presents Tier 1 (board + goal + always-visible history + move
feedback), gates Tier 2 to the first win, and puts recipes/rebinding in a menu (GUI) or tab/panel
(TUI), per the compliance rows 16–19.

**Includes the two onboarding refinements the wxPython oracle settled** (see
`tasks/archive/2026/10/31/how-to-play-welcome-screen.md`): the **goal line lives in the status bar / a terse status
area**, not a space-eating banner; and the **"How to Play" is a dismissible first-run panel**
(with a legal/illegal-move diagram and "don't show again"), reopenable from a **Help** entry — not
a static welcome screen with game screenshots. Each medium adapts these (a CLI prints the rules on
first run and on a `help` command; a TUI uses a status line + a toggled panel).

**And the Tier-3 Recipe-menu shape the oracle settled** (see `tasks/archive/2026/10/31/recipe-menu-direct-recipes.md`):
each **saved recipe is a submenu → View / Apply**, with **Save** as the menu's first item; no
"Apply…/Show…/List…" chooser verbs. A TUI lists recipes as selectable rows with the same two actions.

## Context (cold-start orientation)

- **Read first:** `tasks/reference/ui-design-principles.md` (the tiers + rationale),
  `tasks/reference/feature-spec.md` §3.5 + rows 16–19, and the oracle implementation in
  `python/src/hanoigame/hanoigui.py` (the reference for what each tier looks like).
- **The shared-XRC decision is SETTLED: option (b) — each wx front-end does the tier wiring
  programmatically; `ui/hanoi.xrc` is NOT restructured.** (Decided William Emerison Six
  <billsix@gmail.com>, delegated to the agent 2026-11-01; confirmed by the oracle itself.) The
  wxPython oracle (`python/src/hanoigame/hanoigui.py`) already does exactly this, and its own comments
  state why (lines ~39, ~358, ~408): it *hides* the XRC recipe sidebar and *builds the Recipe menu +
  the history/goal/how-to panels in code* **specifically so the shared XRC stays as-is "for the other
  wx front-ends."** So C++ wx and Rust wxDragon each replicate that programmatic surgery in their own
  code; the XRC is left alone. Rationale for (b) over (a) [baking the tier structure into the XRC]:
  the oracle is already merged and working on the unchanged XRC, so restructuring the XRC now would
  force reworking the merged oracle and risk regressing all three wx UIs at once — (b) keeps each
  front-end independent and the shared XRC stable. The two are therefore NOT a coupled unit anymore;
  do C++ wx and Rust wxDragon independently.
- **NOT done in the overnight batch (needs on-display sign-off), deliberately:** the wx trio
  (C++ `cpp/hanoiwx.cpp` + Rust `rust/hanoi-gui`) is ~500 lines of programmatic UI surgery mirrored
  across C++ wxWidgets and Rust wxDragon (whose build compiles wxWidgets from source); a
  compile + headless-smoke cannot confirm it *looks* right, which is exactly what these need. Left for
  a session where the maintainer can watch `make wx` (C++) / `make wx` (Rust) live. Plan below.
- **Per-UI notes:** the Rust Tauri app and ratatui TUI already had parity gaps (no three-panel view;
  no valid-moves line) per `feature-spec.md` §"Other implementations"; fold those fixes in here. A
  plain CLI states Tier-2 gating in text rather than disabling a control (§6.1).

## Plan — the remaining wx trio (C++ `cpp/hanoiwx.cpp` + Rust `rust/hanoi-gui`)

Everything else is DONE (text UIs, C++ ImGui, Rust egui, Rust Tauri). Only the two wx front-ends
remain. **Template = the merged wxPython oracle `python/src/hanoigame/hanoigui.py`** — port its
programmatic learning-flow surgery into each, leaving `ui/hanoi.xrc` unchanged (decision above). Both
currently sit at the PRE-learning-flow layout the XRC defines: recipe sidebar panel, Relabel already a
menu, status bar (C++: field 0 status + field 1 moves), About-only Help, and Tier-2 gated per
*current* game (`!won`) rather than a first-win latch. Per front-end, mirror the oracle's methods:

1. **Hide the recipe sidebar** (don't remove it from the XRC): the C++ `build_ui`/Rust equivalent
   collapses the `recipe_list` + Save/Apply/Show box (oracle `_hide_recipe_sidebar`).
2. **Recipe menu** inserted after Relabel (Game, Relabel, Recipe, View, Help): "Save current solution"
   first (enabled only at a win, auto-name `solve-N`), then each saved recipe → View / Apply
   (oracle `_build_recipe_menu`/`_rebuild_recipe_menu`; the existing `on_save`/`on_apply`/`on_show`
   handlers move onto it). Keep the existing three-panel RebindingDialog + RecipeDialog from the XRC.
3. **Always-visible Tier-1 history panel** built in code to the right of the board (a `wxListBox` of
   the default-label tally with a header `N moves (optimal 2^N-1)`), fed from `recorder.default_moves`
   via `format_move_tally` (oracle `_build_history_panel`/`_update_history`); add a **View → Move
   history** check toggle.
4. **Goal line** in the status bar: lead with `Goal: move all N discs to peg 3` (oracle put the goal
   in the status area, not a banner). C++ already has a 2-field status bar — add the goal (a 3rd field
   or fold into field 0) + keep `Moves: N`.
5. **How to Play**: a first-run dismissible panel/dialog (the goal + the one rule + a legal/illegal
   `✓/✗` diagram + "don't show again" via the platform config store), reopenable from **Help → How to
   Play** (oracle `_build_howto_panel`, `HOWTO_TEXT`; C++ Help currently has only About).
6. **Tier-2 `won_once` latch**: replace the `!won` (current-game) gating of the Relabel + Recipe menus
   with a session latch set on the first win (dim-don't-remove) — the Relabel menu items already dim
   via `refresh()`; switch the predicate to `won_once`.

**Caveats for the implementer:** wxDragon (Rust) is limited to `wxDC` (no `wxGraphicsContext`) and has a
narrower API than C++ wxWidgets — the oracle's panels may need simpler equivalents (see
`tasks/reference/rust-gui-tui-and-ecosystem.md`); its first build compiles wxWidgets from source (slow).
Verify: C++ `cd cpp && make -o image build` + a headless Xvfb launch smoke; Rust `cd rust && make check`
(wxDragon compiles under `--all-targets`) + `make wx` on a display. **Both need the maintainer's
on-display `make wx` sign-off** before merge. When the trio lands, harvest this settled XRC decision
into `tasks/reference/ui-design-principles.md` (ruling #? — "wx front-ends carry the learning flow in
code, XRC stays shared and structural").

## Related

- `tasks/reference/ui-design-principles.md`, `tasks/reference/feature-spec.md` (§3.5, §6, rows 16–19).
- `tasks/archive/2026/10/31/ui-learning-flow-spec-and-wxpython.md` — the oracle this mirrors.
- `tasks/archive/2026/10/31/how-to-play-welcome-screen.md` — the onboarding refinements (status-bar goal + first-run
  How-to-Play panel) done wxPython-first; this fan-out carries them to the other front-ends.
- `tasks/archive/2026/10/31/recipe-menu-direct-recipes.md` — the Tier-3 Recipe-menu shape (recipes as View/Apply
  submenus) done wxPython-first; this fan-out carries it too.
- `tasks/fan-out-move-tally.md` — the move-tally fan-out this absorbs for GUI/TUI presentation.
- Parity gaps to fold in: `tasks/archive/2026/10/25/rust-feature-parity-tauri-tui-gaps.md`.
