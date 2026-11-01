# Document the learner's knowledge state at each step of the UX

**Status:** proposed — needs go-ahead.
**Priority:** 6 **Difficulty:** 4
**Created:** 2026-11-01 (William Emerison Six <billsix@gmail.com>). Follows the win-celebration work
(archived `tasks/archive/2026/11/01/win-celebration-recipe-discovery.md`) and its UX write-up.

## BLUF

The UX reference docs describe *what each surface does* and *why*, but not the thing underneath it: a
**model of what the learner KNOWS at each step** — what we assume they already know entering a step, what
that step teaches, and what they know leaving it. hanoi's whole premise is a user who does **not** know
Towers of Hanoi or the "solve small, relabel, replay" method (feature-spec §1), so the ordering of what
is taught when is the core design risk. This task produces an explicit **per-step knowledge-state
progression** and uses it to **audit the flow for gaps** — any step that assumes knowledge the user has
not been given yet, or teaches something before it is useful. "Done" = the progression is written into
the reference layer (see the open question on where), every step's `assumes / teaches / knows-after` is
stated, and any ordering gap it surfaces is either fixed or logged as its own task.

## Context (read first)

- `tasks/reference/win-celebration-and-recipe-discovery-ux.md` — the win → teach → save flow (the most
  recent, most detailed step); this task generalizes that "teach once, at the hinge" thinking to the
  whole journey.
- `tasks/reference/ui-design-principles.md` — the Apple-HIG three-tier progressive-disclosure flow (the
  tiers are *when* things appear; this task is about *what the learner knows* by then).
- `tasks/reference/feature-spec.md` §1 (teaching intent), §3.5 (learning flow), §4 (the features in the
  order they become relevant).
- It is **UI-agnostic** — the knowledge-state model is about the learner, shared by every front-end
  (GUI and text); individual UIs then realize the teaching per their medium.

## Plan

1. **Enumerate the journey steps**, in order, e.g.: cold start → "How to Play" shown → first
   legal/illegal moves → first win (the teaching modal: recipes introduced) → Tier-2 unlock → first
   relabel → first recipe save (at the discard boundary) → first apply → first **rebinding view** →
   subsequent wins. (Refine the list against the actual flow.)
2. **For each step, state three things:** (a) what the learner is **assumed to know** entering it, (b)
   what the step **teaches / makes available**, (c) what they **know leaving it**. A compact table or a
   state list.
3. **Audit for ordering gaps:** any step that assumes un-taught knowledge (e.g., does "Apply a recipe"
   assume the user understands relabelling? is the three-panel rebinding view legible given only what
   they have learned by then?), or teaches a concept before it is useful. Flag each; fix the small ones
   inline, log the larger ones as their own tasks.
4. **Write it into the reference layer** (see open question 1) and cross-link from
   `ui-design-principles.md` and the win-celebration UX doc.
5. **Keep it honest to the implementation** — where the model says "the user now knows X", confirm a UI
   step actually taught X (don't assume implicit teaching suffices for a non-knower, per §3.5).

## Open questions

1. **Where should the progression live?** (a) a new section in
   `tasks/reference/win-celebration-and-recipe-discovery-ux.md`; (b) a new dedicated reference doc
   `tasks/reference/learner-knowledge-states.md` cross-linked from `ui-design-principles.md`; or (c) a
   section inside `ui-design-principles.md` itself (it already owns the three-tier flow). **Recommend
   (b)** — a dedicated doc: the progression is a distinct, reusable lens (and could grow a per-step
   table), and keeping `ui-design-principles.md` lean is the house preference. Your call.
2. **How formal?** A prose "assumes / teaches / knows-after" per step is enough to start; a fuller state
   machine (with the branches — e.g. a player who never relabels) is optional. **Recommend** the prose
   table first, note branches only where they change what must be taught.

## Related

- `tasks/reference/ui-design-principles.md`, `tasks/reference/win-celebration-and-recipe-discovery-ux.md`,
  `tasks/reference/feature-spec.md` §1/§3.5/§4.
