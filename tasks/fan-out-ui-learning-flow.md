# Fan out the learning-flow UI to every other front-end

**Status:** proposed — needs go-ahead (do after the maintainer approves the wxPython oracle).
**Priority:** 3
**Difficulty:** 6

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
