# Learner knowledge states — the hanoi UX as a state machine

**Reference document.** Models the hanoi learner's journey as a **state machine over their KNOWLEDGE**:
each state is what the player knows, each transition is a UI event that teaches or unlocks something, and
the branches capture the optional paths. Its job is to make the teaching **order auditable** — so no UI
step depends on knowledge the player has not been given yet, and nothing is taught before it is useful.
**UI-agnostic** (every front-end realizes these transitions in its own medium). Grounded in
`tasks/reference/ui-design-principles.md` (the three-tier flow) and `tasks/reference/feature-spec.md`
§1/§3.5. Not a task; update in place. Created 2026-11-01 (William Emerison Six <billsix@gmail.com>).

## Why model knowledge, not screens

hanoi teaches a user who starts knowing **nothing** about Towers of Hanoi or the "solve small, relabel,
replay" method (feature-spec §1). The core design risk is **ordering**: teaching a concept before it is
useful, or — worse — a step that assumes knowledge the user has not been given. Tracking the *screens*
doesn't catch that; tracking the *learner's knowledge* does. The audit rule this doc exists to support:

> **A transition's teaching must not assume knowledge absent from its source state.**

## The states (what the learner knows)

- **S0 — Cold start.** Knows nothing: not the goal, not the legal-move rule, not the method.
- **S1 — Onboarded.** Knows the **goal** (all disks to peg 3) and the **one legal-move rule** (move a
  peg's top disk; never a larger disk onto a smaller). Has been *told* a method exists ("solve small,
  relabel, replay") but does **not** yet understand it.
- **S2 — First solve.** Knows they can solve a small stack by hand, and — from the first-win teaching —
  that **recipes** exist (a solved game can be saved and replayed). Tier 2 is now unlocked. Does not yet
  have a saved recipe, nor understand relabelling concretely.
- **S3 — Has a recipe.** Knows a solution can be **saved** (named `solve-N`) and later listed / viewed /
  applied.
- **S4 — Relabelled.** Knows the **label vs. physical-peg** distinction: relabelling renames the pegs (a
  permutation of 1,2,3), colour follows the label, disks don't move.
- **S5 — Method understood (graduated).** Has **applied a recipe under a relabelling** and seen the
  **three-panel rebinding view** — watched a small solve become the moves that advance a bigger puzzle.
  The method is now concrete, not just words. This is the lesson the whole program exists to deliver.

## The transitions (events; what each teaches)

```
                app opens
    S0 ───────────────────────▶ "How to Play" modal
                                 (goal + legal rule + the method is NAMED)
                                         │
                                         ▼
    S1 ──make moves; legal/illegal feedback teaches the rule──▶ (win)
                                         │
                                         ▼  first-win teaching modal
    S2  ── recipes introduced; Tier 2 (Relabel + Recipe) unlocks ──
         │
         ├─ relabel the pegs ─────────────────────────────▶ S4
         ├─ New Game → "Save solution?" → Save ───────────▶ S3
         ├─ Recipe menu → Save (post-win) ────────────────▶ S3
         └─ (ignore Tier 2) ──────────────────────────────▶ stays S2
         
    S3 ∧ S4 ── apply a recipe under a relabelling ─────────▶ S5
                                 (the three-panel rebinding view = the payoff)
```

Wording and widgets differ per front-end (a GUI modal vs. a printed block; the save offered at the
new-game boundary in a GUI, inline at the win in a text UI — see the win-celebration UX doc); the
**knowledge transitions above are shared by every UI**.

## The branches (and the dependency that matters)

- **Order of S3 and S4 is free.** From S2 a learner may relabel first (→S4) or save first (→S3); neither
  blocks the other.
- **S5 requires BOTH S3 and S4.** You cannot reach the rebinding-view payoff without (a) a saved recipe
  to apply and (b) a non-default labelling (the rebinding view is shown *only* when relabelled,
  feature-spec §4.8). The UI gates this naturally: Apply needs a saved recipe; the rebinding view appears
  only under a relabelling.
- **The skip-the-payoff branch — a real gap to watch.** A learner can save a recipe (S3) and **apply it
  WITHOUT relabelling** → no rebinding view → they never see the core lesson. They are "done" mechanically
  but have not learned the method. Mitigation today: the first-win teaching *names* relabelling as the
  point (nudging toward S4), and the three-panel view is deliberately withheld under the default
  labelling (nothing to teach there). Whether to nudge harder — e.g. suggest relabelling after the first
  save — is an **open design question, not a bug**.
- **Never-relabel branch.** A learner who only ever replays recipes under the default labelling stays at
  S3 and solves bigger stacks mechanically; the program still "works" but the lesson lands only at S5.
- **Optimality is orthogonal.** Winning optimally vs. over the minimum changes the celebration *text*
  (feature-spec §4.9), not the knowledge state.

## The audit (does any step assume un-taught knowledge?)

| Transition | Assumes (source-state knowledge) | Teaches / unlocks | Verdict |
| --- | --- | --- | --- |
| S0 → S1 (How to Play) | nothing | goal, legal rule, method named | ✓ |
| within S1 (move feedback) | goal + rule (from How to Play) | the rule, concretely | ✓ |
| S1 → S2 (first win teaching) | just solved it by hand | recipes exist; Tier 2 | ✓ |
| S2 → S3 (save at discard / menu) | recipes introduced (S2) | a recipe persists as `solve-N` | ✓ |
| S2 → S4 (relabel) | *why* reuse (named at S2) | label vs. peg; colour-by-label | ✓ (watch: relabelling before understanding *why* can confuse; the physical 1-2-3 reference row mitigates) |
| S3 ∧ S4 → S5 (apply + rebinding view) | a recipe (S3) **and** a relabelling (S4) | the method, made concrete | ✓ prerequisites gated by the UI; **the rebinding view is the highest-risk surface** — it must be legible given only S1–S4 knowledge, and is the one most worth user-testing |

## Cross-links

- `tasks/reference/ui-design-principles.md` — the three-tier flow (the *when* a thing appears; this doc
  is the *what the learner knows* by then).
- `tasks/reference/win-celebration-and-recipe-discovery-ux.md` — the S1→S2 win step and the S2→S3 save in
  detail.
- `tasks/reference/feature-spec.md` — §1 (teaching intent), §3.5 (learning flow), §4.3 (relabel), §4.5
  (save), §4.8 (rebinding view), §4.9 (win).
