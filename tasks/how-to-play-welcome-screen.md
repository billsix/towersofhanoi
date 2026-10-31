# How-to-play / welcome screen (first-run + Help menu)

**Status:** wxPython implementation DONE 2026-10-31 (staged, maintainer commits); the fan-out to the
other front-ends is tracked by `tasks/fan-out-ui-learning-flow.md`. Archive after the work commit
exists (owed, own commit). On-display `cd python && make wx` is the maintainer's last check.
**Priority:** 4
**Difficulty:** 3

## Work record (wxPython, 2026-10-31)

- **Goal line → status bar.** The status bar is now **3 fields** — `[goal | action-feedback |
  moves]`, widths `[-1, -2, 140]`. `_update_goal` writes a terse "Goal: move all N discs to peg 3"
  to field 0 (the full rules moved into the panel); `_set_status` → field 1; the moves counter →
  field 2. The old bold goal `wx.StaticText` banner is gone.
- **How-to-Play panel** (`_build_howto_panel`, replaces the old `wx.CollapsiblePane`): heading + the
  rules text + a small **legal/illegal-move diagram** (`_LegalMoveDiagram`, custom `wx.GraphicsContext`
  paint: ✓ smaller-on-larger, ✗ larger-on-smaller struck through) + a **"Don't show this again"**
  checkbox + a **"Got it"** button. Shown on first run; hidden if the preference says so. Non-modal,
  in-window (not a board-blocking dialog).
- **Reopen + persistence.** **Help → How to Play** (added programmatically, shared XRC untouched)
  reopens it; the **View → How to play** check item mirrors/toggles it; both go through `_show_howto`.
  "Don't show again" persists via **`wx.ConfigBase.Get()`** (key `show_howto_on_start`); `main()` sets
  the app/vendor name so the store is stable across runs.
- **Verification:** `make format` / `type-check` / `test` green (130 passed / 2 skipped); headless
  Xvfb smoke (`tasks/adhoc/drag-drop-spike/gui_smoke.py`) now also asserts the panel builds, Help
  shows it, "Got it" hides it, and the goal sits in status field 0. The *look/feel* is the
  maintainer's on-display call (`make wx`).
- **ty gotcha:** the wxPython stubs expose `wx.ConfigBase` but **not** `wx.Config` (real at runtime) —
  use `wx.ConfigBase.Get()`.

## BLUF

Give the learner who does **not** know Towers of Hanoi a proper first-run **"How to Play"** — the
goal, the one legal-move rule, and how to act on the board — presented the way the Apple HIG actually
endorsed (brief, dismissible, re-openable from **Help → How to Play**, pointing at the *live* board
rather than static screenshots). This absorbs the teaching load now carried by the oversized
always-visible goal banner, which then shrinks. "Done" = a wxPython first-run panel + a Help-menu
entry that reopens it, folding in the existing Tier-1 collapsible "How to play" pane so there is one
source of truth; then rolled into `fan-out-ui-learning-flow.md` for the other front-ends.

## Context (cold-start orientation)

- This is the concrete form of **ruling #4 "Onboarding for the non-knower"** in
  `tasks/reference/ui-design-principles.md` (always-present goal + dismissible "How to play") and
  compliance row 19 / the Onboarding note in `tasks/reference/feature-spec.md` (§3.5, lines 79, 268).
  Those say onboarding must exist; this task settles its **shape**.
- **Trigger (maintainer, 2026-10-31):** after merging the learning-flow redesign, the always-visible
  goal label ("Goal: move all 3 discs from peg A to peg C") was found to **eat too much screen space**
  in the wxPython GUI. The maintainer asked whether the HIG supports a welcome / "how to play" screen,
  possibly reachable from the Help menu, and asked to log the recommended design here.
- **Where it lives (wxPython, the oracle front-end):** `python/src/hanoigame/hanoigui.py` already has
  `_build_onboarding` (the goal line + a `wx.CollapsiblePane` "How to play") and a Recipe/View menu bar.
  The C++ ImGui app (`cpp/main.cpp`) already has a **Help → Controls / About** modal (`draw_help_modal`)
  — a partial precedent to reuse when this rolls out there.

## What the Apple HIG actually says (grounding for the design)

- **Apple shipped onboarding — but optional and non-trapping.** The 1984 Mac came with a *Guided
  Tour*; a first-run intro is in-tradition, *provided* it is dismissible, re-openable, and not a mode
  you must clear on every launch (User Control + Modelessness — don't trap the user in a dialog).
- **Prefer the live interface over pictures of it.** The progression Balloon Help (System 7) →
  **Apple Guide** (System 7.5) moved toward *active assistance*: coachmarks pointing at the **real,
  live control** and having the user do the real task — not screenshots describing it. Our board is
  interactive and already on screen, so a screenshot of it is a strictly worse, dead copy.
- **Recognition over recall.** The intro must be retrievable (**Help → How to Play**) so the user
  never has to remember how to summon it.

## Recommended design (logged as the maintainer asked; refine on go-ahead)

1. **First-run "How to Play" panel** shown once on first launch: the goal in one sentence, the **one
   rule** (never place a larger disc on a smaller one), and the action ("drag the top disc onto
   another peg — or use the move buttons"). Dismissible, with **"Don't show this again"** (persisted in
   per-user config). Non-blocking: a side/overlay panel that does **not** cover the board on every
   launch — not a hard modal gating the game (that is the "mode" the HIG warns against).
2. **Re-openable from Help → How to Play** at any time (recognition, not recall). This is the
   maintainer's "could also be activated under the Help menu."
3. **No static game screenshots.** Where a figure earns its place, illustrate the **rule**, not the
   app: a small **legal / illegal move diagram** (✓ small-on-large, ✗ large-on-small) — that teaches
   the thing beginners get wrong. The live board is the "screenshot."
4. **One source of truth.** Fold today's Tier-1 collapsible "How to play" pane into this panel + the
   Help entry, so we don't ship three overlapping explainers (goal banner + collapsible pane + welcome).
5. **Shrink the goal line.** Once the panel carries the teaching, the always-present goal statement
   drops to a **compact, muted one-liner** (candidate home: the window **status bar**, freeing the top
   area for the board). Ruling #4's "always-present one-line goal statement" is kept — just made small.
   (See open question 1: this is the maintainer's layout call.)

## Decisions already taken (maintainer delegated "log what you think is right", 2026-10-31)

- Reachable from the Help menu: **yes** (the maintainer's own suggestion).
- Screenshots of the game: **no**; use a small legal/illegal-move rule diagram instead (my
  recommendation, delegated).
- Build wxPython-first (prove it on the oracle front-end), then roll into the fleet via
  `fan-out-ui-learning-flow.md` — matches how the learning-flow redesign itself was done.

## Open questions — resolved (maintainer, 2026-10-31)

1. **Goal-line treatment** → **status bar** (implemented, field 0).
2. **Design changes before building** → none; build wxPython-first (both answered "status bar for the
   goal line, build it wxpython-first").

## Related

- `tasks/reference/ui-design-principles.md` — ruling #4 (onboarding), and the Modelessness / User
  Control / recognition-over-recall principles this applies.
- `tasks/reference/feature-spec.md` — §3.5 learning flow, Onboarding note (line 79), compliance row 19.
- `tasks/fan-out-ui-learning-flow.md` — the follow-on that carries this (and the rest of the tier
  redesign) to the C++ ImGui/wx and Rust wx/egui/Tauri front-ends; the C++ `Help → Controls / About`
  modal (`cpp/main.cpp` `draw_help_modal`) is the reuse point there.
- `tasks/archive/2026/10/31/ui-learning-flow-spec-and-wxpython.md` — the redesign that created the
  current goal line + collapsible "How to play" this task supersedes with a single source.
