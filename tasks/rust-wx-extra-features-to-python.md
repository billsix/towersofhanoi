# Rust wx GUI had features the Python wx lacks — decide which (if any) to add to the Python oracle

**Status:** proposed — needs the maintainer's decision (which features, if any).
**Priority:** 6 **Difficulty:** 3 (the decision + a Python impl; the fan-out, if triggered, is its own set)
**Created:** 2026-10-26 (William Emerison Six <billsix@gmail.com>). Spun off from
`tasks/rust-gui-use-shared-xrc.md`: when the Rust wx GUI was migrated to load the shared `ui/hanoi.xrc`
(the Python layout, which the maintainer "already like[s] how … is"), the Rust GUI **lost** a few things
it had that the Python wx doesn't. The maintainer asked: capture those as a task that **asks whether
they belong in the Python wx version**; if yes, implement in Python (the oracle) and then **schedule
fan-out tasks to port them to every UI, including the text ones**.

## BLUF

The Rust wxDragon GUI (pre-XRC-migration) carried UI affordances the Python wx oracle doesn't have.
Migrating Rust to the shared XRC made the Python layout the authority, so those Rust extras were dropped
from Rust. This task lists them and asks, per item, **do you want it in the Python wx GUI?** For each
"yes": implement it in the Python wx (the behaviour oracle) first, update `feature-spec.md`, then this
task **schedules a fan-out task per accepted feature** to port it to all UIs (Python CLI/TUI, C++
ImGui/wx, Rust CLI/TUI/wx/Tauri) — mirroring the move-tally pattern
(`tasks/wxpython-running-move-tally.md` → `tasks/fan-out-move-tally.md`).

## The Rust-wx-only items (verified 2026-10-26 against `hanoigui.py` + `ui/hanoi.xrc`)

1. **A "How to play" help dialog** — the Rust GUI's Help menu had **How to play** (a dialog explaining
   moves, relabelling, recipes, new game) *in addition to* About. The Python wx menu (and the XRC) has
   **About only**. → Add a "How to play" item to the Python wx? (Recommend yes — it's good teaching
   surface, and this is a teaching project; the text already exists in the old Rust `ID_HELP` handler.)

(That is the only genuine feature gap. The other Rust/Python differences are *presentation*, not
features, and were resolved by conforming Rust to the XRC: the board was two stacked widgets in Rust vs
the XRC's one `board_slot`; the board-style menu was check items in Rust vs **radio** in the XRC; the
six move buttons were a flat row in Rust vs three from-peg columns in the XRC. And where they differ the
*Python* is richer — the recipe-show / rebinding views are scrollable 3-panel dialogs in Python but
plain `MessageDialog`s in Rust — so those are gaps the other way, tracked by the normal parity audit,
not here.)

## Plan

1. **Maintainer decides** per item in "The Rust-wx-only items" (just #1 today): add to the Python wx, or
   drop permanently? (Open question 1.)
2. For each accepted item: implement it in the **Python wx GUI** (`python/src/hanoigame/hanoigui.py`),
   keeping the shared `engine`/`commands`/`presenter` layering; update `feature-spec.md` (new §4.x + a §7
   row) from the implementation, the way the move tally was finalized.
3. **Schedule the fan-out**: once the feature is in the Python oracle + spec, create a fan-out task (or
   fold into `tasks/fan-out-move-tally.md`'s pattern as a sibling) to port it to every UI, **including
   the text ones** (CLI/TUI) where it makes sense (e.g. "How to play" is just a `help`-style text block
   there — the CLI/TUI already have `help`, so check whether it's already covered before fanning out).
4. If a wx feature genuinely doesn't belong in a text UI, say so in that fan-out task rather than forcing
   it.

## Open questions

1. **"How to play" dialog — add it to the Python wx (then fan out), or drop it?** Recommend add: the
   content exists (old Rust handler), it's a teaching aid, and the CLI/TUI already have `help` so the
   fan-out there may be a no-op or a small alignment. Your call.

## Related

- `tasks/rust-gui-use-shared-xrc.md` — the migration that dropped these from Rust (the parent).
- `tasks/reference/feature-spec.md` — where an accepted feature gets specified before fan-out.
- Pattern precedent: `tasks/wxpython-running-move-tally.md` + `tasks/fan-out-move-tally.md` (build in the
  oracle → spec → fan out to all UIs).
- The old Rust "How to play" text: `tasks/rust-gui-use-shared-xrc.md` points at the pre-migration
  `rust/hanoi-gui/src/main.rs` `ID_HELP` handler (in git history after the migration lands).
