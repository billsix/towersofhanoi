# Click a move in the history panel to review the board as it was then

**Status:** proposed — needs go-ahead (open questions below)
**Priority:** 4
**Difficulty:** 6 (a core change in Python and Rust, then five GUIs)
**Created:** 2026-11-21 (William Emerison Six <billsix@gmail.com>)

## BLUF

Make each row of the always-visible **move history** panel clickable. Clicking move *k* shows the
board as it stood right after move *k*, so the student can step back through what they did and study
it. While reviewing a past state the student must not end up in a state that makes no sense: either
moves are blocked until they return to the present, or making a move asks "Continue from move *k*?
This deletes moves *k+1*…*n*." Done = review mode works in every graphical UI, built on one
shared-core API, and the feature spec describes it.

## Context

- Read first: `tasks/reference/feature-spec.md` §4.11 (move history contract: numbered, default
  1-2-3 labels, moves only, reset per game) and §3.5 (learning-flow tiers),
  `tasks/reference/ui-design-principles.md`, `tasks/reference/learner-knowledge-states.md`.
- The history is moves only, in **default-label space**; relabels are not listed. So "the state at
  move *k*" = replay the first *k* moves from the start position. The labelling shown while
  reviewing is Open question 3.
- Keep the front-ends thin (repo `CLAUDE.md`): put "state after *k* moves" and "truncate to *k*
  moves" in the shared core (Python `python/src/hanoigame/engine.py` / `hanoimodel.py`, mirrored in
  `rust/hanoigame/`; C++ has its own engine in `cpp/`), with unit tests, then have each GUI call it.
- The Python wx history panel: `HanoiFrame._build_history_panel` / `_update_history` in
  `python/src/hanoigame/hanoigui.py` (a `wx.ListBox`, `self._history_list`).
- Interaction with other state: the move count vs optimal, the win state (reviewing a won game's
  middle should not un-win it), the "Save recipe" item (enabled only on a win), and drag-and-drop
  (`set_interactive(False)` in review mode, as after a win).

## Plan

1. Core: `state_after(k)` (pure replay) and `truncate_to(k)`, plus tests, in Python then Rust (and the
   C++ engine).
2. Python wx oracle: click a row → review mode (board shows state *k*, a banner "Reviewing move *k*
   of *n*" with a "Back to current" button, the row highlighted); arrow keys step through rows.
3. Maintainer's on-display check, then fan out to C++ ImGui, C++ wx, Rust wxDragon, egui, Tauri.
4. Feature spec §4.11 + a compliance row; each subproject's gate.

## Open questions

1. **A move made while reviewing:** (a) block it until "Back to current" is pressed, or (b) ask
   "Continue from move *k*? Moves *k+1*…*n* will be deleted" and truncate on yes? *Recommend (b),
   with the board non-interactive until the student answers; it is the one you described as the goal.*
2. **After a win:** should truncating a won game (continuing from an earlier move) be allowed, so the
   student can try a different line? *Recommend yes; it un-wins the game and disables Save until the
   next win.*
3. **Labelling while reviewing:** show the past board under the **current** labelling, or under the
   labelling that was active at move *k*? The history does not record relabels today, so the second
   needs relabel events added to the history model. *Recommend the current labelling (no model change).*
4. **Text UIs:** should the CLI/TUI get a matching command (e.g. `history <k>` to print the board at
   move *k*)? *Recommend yes, but as a follow-up task, not part of this one.*
