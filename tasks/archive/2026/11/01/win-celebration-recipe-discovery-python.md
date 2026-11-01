# Win celebration + recipe discovery — Python (the oracle)

**Status:** implemented 2026-11-01 — the shared helpers (`presenter.format_win_celebration` +
`default_recipe_name`) and all three front-ends (CLI, curses TUI, wxPython GUI) surface the win
celebration; feature-spec row 20 added. Gate green in-container (ty src+tests, 135 pytest incl. the new
doctest + first-win test, ruff). **Pending:** the maintainer's display-verify of the wxPython win modal
(agent can't drive the display) — then this archives.
**Priority:** 4 **Difficulty:** 4
**Part of:** `tasks/archive/2026/11/01/win-celebration-recipe-discovery.md` (umbrella — read it for the cross-cutting design,
the HIG grounding, and the open questions, which **block implementation here**).
**Next:** `tasks/archive/2026/11/01/win-celebration-recipe-discovery-rust.md`, `tasks/archive/2026/11/01/win-celebration-recipe-discovery-cpp.md`
depend on the wording this task fixes.
**Created:** 2026-11-01 (William Emerison Six <billsix@gmail.com>).

## BLUF

Implement the win celebration in the **Python behaviour oracle first** — it fixes the canonical wording
the spec records and Rust/C++ mirror. Add a **shared core/presenter helper** that returns the
congratulatory + recipe-teaching text from a snapshot, wire the **three Python front-ends**
(`hanoicli.py`, `hanoigame.py` curses TUI, `hanoigui.py` wxPython GUI) to surface it at the win, and
update `feature-spec.md` + the compliance checklist. "Done" = all three Python UIs show the moment
(first-win teaching + lighter later wins), the helper is doctested, and the spec names it as mandatory.

## Context (read first)

- Umbrella design + open questions: `tasks/archive/2026/11/01/win-celebration-recipe-discovery.md`. **Do not implement until
  the umbrella's four questions are addressed** (they set trigger, save-in-popup, core-helper, spec-change).
- Core files: `python/src/hanoigame/presenter.py` (home for the text helper, beside `format_move_tally`),
  `engine.py` (`is_won`/optimal `min_moves`/`save_recipe`; the "first win this session" flag may live on
  the session), `hanoigui.py` (`_save_recipe_with_prompt` already opens with `value=f"solve-{num_disks}"`
  — §4.5), `hanoicli.py`, `hanoigame.py`.
- The GUI onboarding precedent to mirror: "How to play" is a **centered modal shown once** (reopenable) —
  the first-win celebration is the same kind of one-time modal moment.

## Plan

1. **Core helper** (presenter): `format_win_celebration(num_disks, moves, min_moves, first_win)` (exact
   name/signature decided at implementation) → the text with the three parts (congrats+verdict, the
   recipe teaching line, the save affordance / `solve-<N>` default). One source of wording; **doctest it**
   (the oracle's text is the authority — Rust/C++ assert against the same strings).
2. **wxPython GUI** (`hanoigui.py`): on **every** win, a centered celebration (congrats + result + a
   **Save as recipe** action prefilled `solve-<N>`, reusing `_save_recipe_with_prompt`, + a dismiss
   "Not now"/"Got it"); on the **first** win it additionally carries the recipe **teaching** paragraph
   (what recipes are + "solve small, relabel, replay"). Keep the Tier-2 enable.
3. **CLI** (`hanoicli.py`): print the celebration block on **every** win (congrats + result + the
   `save <name>` hint, default `solve-<N>`); the **first** win adds the teaching lines.
4. **Curses TUI** (`hanoigame.py`): surface it in a visible region / one-time overlay consistent with the
   TUI's modeless style; the `save` path stays the Tier-2 command.
5. **Spec** (umbrella Q4): update `feature-spec.md` §4.9 (win surfaces the celebration), §3.5 (the hinge
   is realized, not just menu-enable), §4.5 (the save prompt is part of the first-win moment), and add
   **compliance row 20** ("Win celebration + recipe discovery"). Update `ui-design-principles.md` only if
   the rationale needs a ruling (likely a one-line addition to the Tier-2 paragraph).
6. **Verify:** `make test` (doctests + unit) + `make format`/type-check green; the maintainer runs the
   wxPython GUI to see the first-win modal (agent can't drive the display).

## Open questions — resolved

- The umbrella's four are **resolved** (2026-11-01): teaching explanation **first-win-only**; congrats +
  **Save offer (prefilled `solve-<N>`) every win**; **shared** presenter helper; **update the spec**. No
  Python-specific open question remains — the helper's exact name/signature is implementation discretion.

## Related

- Umbrella: `tasks/archive/2026/11/01/win-celebration-recipe-discovery.md`.
- `tasks/reference/feature-spec.md` (the spec this updates; Python is its authority),
  `tasks/reference/ui-design-principles.md`.
