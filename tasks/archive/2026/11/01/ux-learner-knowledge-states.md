# Document the learner's knowledge state at each step of the UX

**Status:** DONE 2026-11-01 — delivered as the reference doc
`tasks/reference/learner-knowledge-states.md` (a state machine over the learner's knowledge, with the
branches), cross-linked from `ui-design-principles.md` and the win-celebration UX doc.
**Priority:** 6 **Difficulty:** 4
**Created:** 2026-11-01 (William Emerison Six <billsix@gmail.com>). Followed the win-celebration work
(`tasks/archive/2026/11/01/win-celebration-recipe-discovery.md`).

## What was delivered

A model of **what the learner KNOWS at each step** — what a step assumes entering it, what it teaches,
and what they know leaving it — so the flow never depends on un-taught knowledge, built as a **state
machine with branches** (the maintainer's two decisions: a dedicated reference doc; a state machine, not
a prose table). It lives at `tasks/reference/learner-knowledge-states.md`:

- **States** S0 cold start → S1 onboarded → S2 first solve → S3 has a recipe / S4 relabelled → S5 method
  understood (the rebinding-view payoff).
- **Transitions** (what each UI event teaches) and the audit rule: a transition must not assume knowledge
  absent from its source state (with an audit table confirming each one).
- **Branches:** free S3/S4 order; the **apply-without-relabel "skip the payoff" gap** (flagged as an open
  design question, not a bug); the never-relabel path; optimality is orthogonal.

## Follow-on (not required)

The reference doc flags one **open design question** worth a future look: a learner can save and apply a
recipe *without ever relabelling* and so never see the method's payoff (the three-panel rebinding view).
Whether to nudge harder toward relabelling after the first save is a design call — logged in the
reference doc, not scheduled here.

## Related

- `tasks/reference/learner-knowledge-states.md` (the deliverable), `tasks/reference/ui-design-principles.md`,
  `tasks/reference/win-celebration-and-recipe-discovery-ux.md`, `tasks/reference/feature-spec.md`.
