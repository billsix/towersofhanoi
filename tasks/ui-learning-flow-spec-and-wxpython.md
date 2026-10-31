# Learning-flow UI redesign — spec + wxPython (the oracle)

**Status:** proposed — plan and all wx-layout specifics agreed; ready to start on go-ahead.
**Priority:** 2
**Difficulty:** 5

## BLUF

Reorganize hanoi's UI around the **learner's journey** (Apple-HIG progressive disclosure) instead of
the program's domain model, starting with the spec and the wxPython oracle. Three tiers: Tier 1 (board
+ goal + **always-visible move history** + legal-move feedback) is the whole first-solve experience;
Tier 2 (relabelling + recipes) is revealed **at the first win**; Tier 3 (recipe list/show/apply + the
rebinding table) moves into a **menu** (GUI). Done = `feature-spec.md` has a "Learning flow /
progressive disclosure" section citing `ui-design-principles.md`, and the wxPython GUI implements the
three tiers with the move history as an always-visible panel. The fan-out to the other 5 UIs is a
separate follow-on task.

## Context (cold-start orientation)

- **Read first:** `tasks/reference/ui-design-principles.md` (the new rationale, Apple-HIG-grounded —
  the *why* and the tier definitions) and `tasks/reference/feature-spec.md` (the *what* — features,
  §4.11 move tally, §4.8 rebinding view, §6 UI-category guidance). The wxPython GUI is the **oracle**:
  `python/src/hanoigame/hanoigui.py` (XRC-driven; UI in `ui/hanoi.xrc` via the symlink).
- **The problem being fixed:** the earlier UIs surface recipes, relabelling, and rebinding all at once,
  which is noise for a novice who does not yet know the puzzle and can't save a recipe until after a
  win (§4.5). The move history — the primary feedback artifact — was only added as an **on-demand**
  Ctrl+H dialog (§4.11, `tasks/archive/2026/10/26/wxpython-running-move-tally.md`). This redesign
  inverts that hierarchy.
- **Agreed decisions (William Emerison Six <billsix@gmail.com>, 2026-10-31):**
  1. Move history → **always-visible panel** (the Ctrl+H menu item may remain as a focus shortcut).
  2. Recipes → **Tier 3**, in a menu (GUI).
  3. Relabelling → **gated into Tier 2**, introduced at the first-win moment, available thereafter.
  4. Onboarding → add an always-present **goal line** + a dismissible **"How to play"**.
  5. **Spec-first:** update `feature-spec.md` before the wxPython code.

## Plan

### Phase 1 — spec (spec-first)
- Add a **"Learning flow / progressive disclosure"** section to `feature-spec.md` defining the three
  tiers and the four rulings, pointing at `ui-design-principles.md` for the rationale. Refine §6
  (UI-category guidance) to reference the tiers. Supersede §4.11's on-demand framing with
  "always-visible panel (on-demand focus optional)". Add compliance-checklist rows for: always-visible
  move history, Tier-3 recipe placement, Tier-2 relabel gating, onboarding (goal line + How to play).
- Keep Python as the oracle: the spec leads, the code follows.

### Phase 2 — wxPython GUI (`python/src/hanoigame/hanoigui.py` + `ui/hanoi.xrc`)
- **Tier 1:** always-visible move-history panel (content from `presenter.format_move_tally`, numbered,
  default-label space, live count vs `2^N−1`, moves-only, reset per game); always-present goal line;
  dismissible "How to play".
- **Tier 2:** relabelling + recipe-save gated until the first win; the win dialog becomes the teaching
  handoff ("solved N in M moves — save it, start N+1, reuse it under a relabelling").
- **Tier 3:** recipe list / show / apply + the three-panel rebinding view behind the Recipe menu.
- Preserve the HIG-matching behaviours already present: dim-don't-hide move buttons, colour-by-label,
  the three-panel rebinding view (§4.8).
- Verify: `cd python && make type-check && make test`, then the maintainer's on-display `make wx` run.

### Phase 3 — docs + staging
- Stage spec + reference-doc + CLAUDE.md pointer + the wxPython changes by path. File the fan-out task.

## Decisions — concrete wx specifics (maintainer deferred to recommendations, 2026-10-31)

1. **Move-history panel placement:** a **right-hand side column**, so vertical move growth reads
   naturally and the board keeps its width.
2. **"How to play" presentation:** a **collapsible inline panel, expanded by default on a fresh game,
   collapsed once dismissed** — always one click away, never modal.
3. **Tier-2 gating mechanism:** before the first win, the Relabel/Recipe menus are **disabled (greyed,
   with a tooltip "available after your first win")** — perceived-stability "dim, don't remove" keeps
   the menubar stable; they are not absent-then-appearing.
4. **"First win" unlock scope:** Tier 2 **unlocks for the rest of the session** once any game is won
   (it does not re-lock on each new game) — a learner who has seen the method keeps access.

## Related

- Rationale: `tasks/reference/ui-design-principles.md`. Feature authority: `tasks/reference/feature-spec.md`.
- Move tally origin: `tasks/archive/2026/10/26/wxpython-running-move-tally.md`.
- Follow-on (to file on completion): fan-out of this flow to the other 5 UIs (Python CLI/TUI, Rust
  cli/tui/wx/tauri/egui, C++ ImGui/wx) — the sibling of `tasks/fan-out-move-tally.md`.
