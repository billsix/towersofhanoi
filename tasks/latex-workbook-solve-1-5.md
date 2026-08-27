# LaTeX workbook: solve Hanoi 1–5, referencing/copying/rebinding previous solutions

**Status:** blocked
**Priority:** 6
**Difficulty:** 4
**Started:** 2026-08-27
**Blocked on:** maintainer answers the Open questions below — chiefly whether this is a NEW standalone
`.tex` workbook or an EXTENSION of the existing Sphinx `byhand*` RST→LaTeX pipeline, which already
does most of this. Settle that before building (the two would duplicate content).
**Recheck:** the Open questions below are answered (maintainer-gated; `/recheck-blocked` surfaces it).

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

1. **"LaTeX based" — new standalone `.tex`, or extend the existing Sphinx `byhand` pipeline** (already
   RST→LaTeX→PDF)? These are very different efforts and would duplicate content if both grow.
   *(Recommend: extend `byhand` — the pattern and the LaTeX build already exist; least duplication.)*
2. **"Solve 1–5"** — the docs stop at 4 with `byhand4` a stub. Is the ask to **finish `byhand4` and
   add `byhand5`**, or to produce a fresh 1–5 artifact from scratch?
3. **Relationship to the existing `workbook/` SVG worksheets** (also PDF, also a printable companion)
   — replace them, supersede them, or add a third parallel artifact?
4. **"Instructions per page"** — one subproblem per physical page (LaTeX `\newpage` layout), matching
   the section-per-subproblem structure of `byhand2.rst`?
