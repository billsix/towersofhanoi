# Win celebration + recipe discovery — Python (the oracle)

**Status:** proposed — needs go-ahead.
**Priority:** 4 **Difficulty:** 4
**Part of:** `tasks/win-celebration-recipe-discovery.md` (umbrella — read it for the cross-cutting design,
the HIG grounding, and the open questions, which **block implementation here**).
**Next:** `tasks/win-celebration-recipe-discovery-rust.md`, `tasks/win-celebration-recipe-discovery-cpp.md`
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

- Umbrella design + open questions: `tasks/win-celebration-recipe-discovery.md`. **Do not implement until
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
2. **wxPython GUI** (`hanoigui.py`): on **first** win, a centered **modal** with the celebration text and
   — per umbrella Q2 — a **Save as recipe** action prefilled `solve-<N>` (reusing `_save_recipe_with_prompt`)
   plus a dismiss ("Not now"/"Got it"); on **later** wins, the lighter inline message. Keep the Tier-2
   enable.
3. **CLI** (`hanoicli.py`): print the celebration block on win, with the `save <name>` hint (name defaults
   `solve-<N>`); lighter line on later wins.
4. **Curses TUI** (`hanoigame.py`): surface it in a visible region / one-time overlay consistent with the
   TUI's modeless style; the `save` path stays the Tier-2 command.
5. **Spec** (umbrella Q4): update `feature-spec.md` §4.9 (win surfaces the celebration), §3.5 (the hinge
   is realized, not just menu-enable), §4.5 (the save prompt is part of the first-win moment), and add
   **compliance row 20** ("Win celebration + recipe discovery"). Update `ui-design-principles.md` only if
   the rationale needs a ruling (likely a one-line addition to the Tier-2 paragraph).
6. **Verify:** `make test` (doctests + unit) + `make format`/type-check green; the maintainer runs the
   wxPython GUI to see the first-win modal (agent can't drive the display).

## Open questions

- Inherit the umbrella's four. **No Python-specific open question** beyond them; the only local choice is
  the helper's exact name/signature, which is implementation discretion once Q3 (core helper) is confirmed.

## Related

- Umbrella: `tasks/win-celebration-recipe-discovery.md`.
- `tasks/reference/feature-spec.md` (the spec this updates; Python is its authority),
  `tasks/reference/ui-design-principles.md`.
