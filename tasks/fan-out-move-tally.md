# Fan out the inspectable move tally (§4.11) to every non-Python UI

**Status:** proposed — needs go-ahead.
**Priority:** 5 **Difficulty:** 5 (spread across UIs/languages; each UI is small, the breadth is the cost)
**Created:** 2026-10-26 (William Emerison Six <billsix@gmail.com>). Phase 3 of
`tasks/archive/2026/10/26/wxpython-running-move-tally.md` (Phase 1 wx oracle + Phase 2 spec done 2026-10-26); split out
per that task's plan ("fan out … scope this as its own task/umbrella when Phase 2 lands").

## BLUF

The inspectable running move tally — every move this game, numbered, in the default 1-2-3 (physical)
labelling, with a live count — is implemented and specified in the wxPython oracle (feature-spec §4.11,
§7 row 15). Bring every other UI to that contract: **Python CLI + ncurses TUI**, **C++ ImGui + wx**,
**Rust CLI + ratatui TUI + wxDragon + Tauri**. Each reuses its implementation's existing recorded
default-space move list (the data already exists — it's the recipe recorder's), presents the numbered
default-space list + live count, moves-only, resetting on new game, matching §4.11. "Done" = each UI
shows the tally, each checked against §4.11/§7 row 15.

## Context (read first)

- **The contract:** `tasks/reference/feature-spec.md` §4.11 (finalized 2026-10-26) + §7 row 15. Read it
  first — it is the parity authority. Key points: numbered lines ``"<n>. <from> -> <to>"``, a live
  count, **moves only** (relabels excluded), **default-label space**, **reset per game**, **on-demand**
  (a view/dialog) OR an always-visible panel.
- **The Python oracle:** `python/src/hanoigame/presenter.format_move_tally(moves)` is the shared
  line-format helper; `hanoigui.py` (`_on_move_tally` / `_update_tally`) is the reference view, sourced
  from `recipe.Recorder.default_moves`. Mirror the line format exactly so all UIs agree.
- **The data is already recorded in every port.** The Rust/C++ engines already record moves in
  default-label space for recipes (that is what `apply`/`show` replay through a relabelling). So, as in
  wx, the tally is a **view of existing state**, not new bookkeeping — check each port's recorder/engine
  for the equivalent of `default_moves`.
- **Don't drift from the oracle.** Each port mirrors `format_move_tally`'s output; where a port has a
  shared helper module (Rust `hanoigame` crate, the C++ engine), add the formatter there and have the
  front-ends call it, like Python.

## Plan (per UI — each small; the breadth is the work)

1. **Python CLI** (`hanoicli.py`) — a `history`/`moves` command (or extend `help`) printing
   `format_move_tally(session.recorder.default_moves)`.
2. **Python ncurses TUI** (`hanoigame.py`) — a key or command to show the list (a pager, like the
   recipe/rebinding overlays).
3. **C++ ImGui** (`cpp/main.cpp`) + **C++ wx** (`cpp/hanoiwx.cpp`) — a window/dialog listing the moves;
   add the formatter to the shared engine.
4. **Rust CLI / ratatui TUI / wxDragon / Tauri** — add a `format_move_tally` to the `hanoigame` crate,
   then a view in each front-end (CLI command, TUI overlay, wx dialog, a Tauri panel + command).
5. Verify each against §4.11/§7 row 15; GUIs get the maintainer's on-display check.

## Open questions

1. **One umbrella + step-tasks, or just this doc?** It touches 4 implementations × several front-ends.
   If a single pass is unwieldy, split into per-language step-tasks under an umbrella (CLAUDE.md
   step-task convention). Recommend: start as this one doc; promote to an umbrella if it gets big.
2. **Presentation per UI** — dialog/overlay vs always-visible panel. The spec allows either; recommend
   matching each UI's existing idiom (the recipe Show/Rebinding overlays in the TUIs/GUIs; a panel in
   Tauri). Mind the token cost of a GUI fan-out — brief any subagents tightly, don't over-fork.

## Related

- `tasks/archive/2026/10/26/wxpython-running-move-tally.md` — Phase 1/2 (the oracle + the spec this fans out).
- `tasks/reference/feature-spec.md` §4.11 + §7 row 15 (the contract).
- Fan-out precedent: `tasks/archive/2026/10/25/program-feature-spec-and-compliance.md` (a spec driving
  multi-implementation work).
