# LaTeX workbook: solve Hanoi 1–5, referencing/copying/rebinding previous solutions

**Status:** in progress — design decided 2026-09-14 (see "Decisions"); building a new standalone `.tex`.
**Priority:** 5
**Difficulty:** 4
**Started:** 2026-08-27

## Decisions (maintainer, 2026-09-14) — this reframes the task

The workbook is **NOT a solved/worked doc** (so it does **not** extend the `byhand*.rst` worked
solutions — those are the opposite, filled-in answers). It is a **blank, printable INDUCTION
worksheet**:

- A **page template per n** (n = 1..5). The student **prints multiple copies** — one for n=2, one for
  n=3, … — and fills them in **by hand**.
- The page has **shapes the student writes disc/peg numbers into, with shapes around them**, laid out
  so that **copying the n solution and relabelling it** shows *why solving n gives n+1*.
- Framed as **mathematical induction, not recursion**: assume you can solve n (you have your filled-in
  n sheet) → therefore you can solve n+1 by using that solution twice, rebound (I/T/G → concrete pegs).
- The student's main activity is **copying and relabelling** — the same I/T/G → peg substitution that
  `byhand2.rst` teaches, but blank for the student to perform.
- **New standalone LaTeX** (TikZ for the shapes), a third printable companion distinct from the
  `byhand*.rst` worked solutions and the `workbook/*.svg` solution diagrams. Lives in `workbook/`.
- Visual design: **agent's discretion** (maintainer: "have fun with it").

## Goal

Maintainer's idea, verbatim: *"Make latex based workbook to solve 1-5, with instructions per page of
referencing previous solutions, copying and rebinding."*

A printable LaTeX workbook that solves the Towers of Hanoi for 1–5 disks, one subproblem per page,
each page instructing the reader to reference the previous solution, copy its steps, and rebind
(the I/T/G peg substitution).

## Context (what already exists — from investigation 2026-08-27)

**Heavy overlap already exists — this is why the approach question below must be settled first:**

- **Sphinx `byhand` docs** — `docs/source/byhand1.rst … byhand4.rst` already implement exactly
  "solve for N, reference the previous solution (`:ref:`), copy the steps, and rebind via the I/T/G
  substitution." `byhand2.rst` is the clearest example (I/T/G → peg substitution tables). These build
  to a **real LaTeX PDF** via `make latexpdf` (entrypoint/entrypoint.sh:27-28), LaTeX toolchain in
  entrypoint/02-install-docs.sh:13-19. **Gap:** `byhand4.rst` is a stub and **`byhand5` does not
  exist** (NOTES.md:93-95).
- **`workbook/` SVG worksheets** — `hanoi1..4.svg` → PDF via **Inkscape** (workbook/Makefile), *not*
  LaTeX; stops at 4, no rebinding text. A second, parallel "printable companion".

So the bullet's intent already exists in two partial forms; the real work is deciding which to grow.

## Plan (draft — depends entirely on Q1)

- If **extend Sphinx**: finish `byhand4.rst` and add `byhand5.rst`, keep the `:ref:`/copy/rebind
  pattern from `byhand2.rst`, one subproblem per page.
- If **new standalone `.tex`**: author a fresh 1–5 workbook, `\newpage` per subproblem, decide its
  relationship to the `byhand` docs and the `workbook/` SVGs.

## Notes / decisions

Recommendation from triage: NEW task doc, but flag the overlap — the design decision (Q1) should be
settled first, else content duplicates across `byhand*.rst`, `workbook/*.svg`, and a new `.tex`.

## Open questions

Resolved 2026-09-14 (see "Decisions"): new standalone `.tex` (NOT extend `byhand`); n = 1..5, one
page template per n; a third artifact alongside `byhand*.rst` and `workbook/*.svg` (distinct purpose —
blank inductive fill-in, not solutions); one n per physical page. Visual/shape design is the agent's
call.
