# Fan out the learning-flow UI to every other front-end

**Status:** IN PROGRESS (autonomous batch; branches `ui-fanout-and-apply-output` [merged],
`ui-fanout-tuis` [merged], `ui-fanout-guis` [merged], `ui-fanout-egui`; gpg off → restored). All
**text UIs done** + the **C++ ImGui GUI** (the reference GUI) + the **Rust egui GUI**; **3 GUIs
remain** (C++ wx + Rust wxDragon via the shared `ui/hanoi.xrc`; Rust Tauri) + **drag-drop** per
graphical UI — all need on-display sign-off.
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
  **Relabel** (central) and the whole **Recipe menu** until the first win; Tier-3 recipes moved into a
  top **menu bar** (`egui::menu::bar`) — Recipe menu = Save current solution (enabled at a win) /
  Reset recording / separator / each saved recipe a submenu → View (`view_recipe`) / Apply
  (`apply_recipe_named`, which counts from the recipe not the suppressed step-log); the first-run
  **How to Play** window (goal + the one rule + the solve-small-relabel-replay method) auto-opens once
  and reopens from a **Help** menu. The web (`#[cfg(wasm32)]`) entry is untouched — same `HanoiApp`.
  `cargo check` clean (own workspace, excluded from `make check`); a headless Xvfb + software-GL launch
  ran 6 s with no panic (EXIT=137 from `timeout -s KILL`, empty log). **On-display `make egui` is the
  visual check.** Drag-drop for egui is still pending (below).
- **Remaining, per UI (needs on-display sign-off):**
  - **C++ wx (`cpp/hanoiwx.cpp`) + Rust wxDragon (`rust/hanoi-gui`)** via the **shared `ui/hanoi.xrc`
    decision** — the coupled trio; settle whether the tier structure moves into the shared XRC (the
    wxPython oracle did it programmatically, XRC untouched). Do these together.
  - **Rust Tauri** (`rust/tauri`): the web frontend.
  - Fold in **drag-drop** per graphical UI incl. ImGui (`tasks/port-drag-drop-to-graphical-uis.md`).

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
- **The shared-XRC decision is the crux.** The wxPython oracle was done *programmatically* so
  `ui/hanoi.xrc` stayed untouched (it is loaded by the C++ wx and Rust wxDragon front-ends too). The
  fan-out must decide whether to (a) move the tier structure into the shared XRC (recipe sidebar out,
  history panel in, etc.) so all three wx UIs share it, or (b) keep each wx UI's tier wiring in its
  own code. Recommend (a) — the shared XRC is the consistency guarantee — but it means changing all
  three wx front-ends together; sequence and verify them as one unit.
- **Per-UI notes:** the Rust Tauri app and ratatui TUI already had parity gaps (no three-panel view;
  no valid-moves line) per `feature-spec.md` §"Other implementations"; fold those fixes in here. A
  plain CLI states Tier-2 gating in text rather than disabling a control (§6.1).

## Plan (sketch — refine per UI on go-ahead)

1. Settle the shared `ui/hanoi.xrc` form (decision above), updating the Python/C++/Rust wx front-ends
   together; re-verify each wx GUI.
2. Per non-wx UI (Python curses/CLI, Rust cli/TUI/Tauri/egui, C++ ImGui): add the goal + always-visible
   history + Tier-2 gating + Tier-3 placement appropriate to the medium.
3. Verify each subproject's gates (`make format`/`check`/`type-check`/`test` as applicable) + a
   headless/on-display run; update the §7 compliance rows per UI.

## Related

- `tasks/reference/ui-design-principles.md`, `tasks/reference/feature-spec.md` (§3.5, §6, rows 16–19).
- `tasks/archive/2026/10/31/ui-learning-flow-spec-and-wxpython.md` — the oracle this mirrors.
- `tasks/archive/2026/10/31/how-to-play-welcome-screen.md` — the onboarding refinements (status-bar goal + first-run
  How-to-Play panel) done wxPython-first; this fan-out carries them to the other front-ends.
- `tasks/archive/2026/10/31/recipe-menu-direct-recipes.md` — the Tier-3 Recipe-menu shape (recipes as View/Apply
  submenus) done wxPython-first; this fan-out carries it too.
- `tasks/fan-out-move-tally.md` — the move-tally fan-out this absorbs for GUI/TUI presentation.
- Parity gaps to fold in: `tasks/archive/2026/10/25/rust-feature-parity-tauri-tui-gaps.md`.
