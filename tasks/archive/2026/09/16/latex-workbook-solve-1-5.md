# LaTeX workbook: solve Hanoi 1–5, referencing/copying/rebinding previous solutions

**Status:** complete
**Completed:** 2026-09-16
**Priority:** 5
**Difficulty:** 4
**Started:** 2026-08-27

## What this was

The maintainer's idea, verbatim: *"Make latex based workbook to solve 1-5, with instructions per
page of referencing previous solutions, copying and rebinding."* The task delivered that artifact:
`workbook/induction-workbook.tex`, a printable, blank, fill-in-by-hand **induction** worksheet.

## What was decided, and why

Investigation (2026-08-27) found the intent already existed in two partial forms — the Sphinx
`byhand1..4.rst` worked solutions (I/T/G → peg substitution, `:ref:` cross-links) and the
`workbook/hanoi1..4.svg` solution diagrams — so the open question was which of the two to grow, since
a careless choice would duplicate content across three places. The maintainer settled it (2026-09-14):
a **new standalone `.tex`**, distinct from both. Reason: the workbook is a **blank fill-in** artifact
(the opposite of the worked `byhand*` solutions), framed as **mathematical induction, not recursion** —
assume you can solve n (your filled-in n sheet), then solve n+1 by using that solution twice, rebound.
One page template per n (1..5), printed and filled by hand; visual design left to the agent.

## What was built

`workbook/induction-workbook.tex` (pdflatex + TikZ; built by `make -C workbook`) — the initial 1..5
workbook. Its layout and pedagogy were then reworked by the follow-on task
`tasks/archive/2026/09/16/redesign-induction-workbook-flow.md` into the shipped form: concrete
numbered pegs 1/2/3 (not I/T/G), a top-to-bottom Part 1 → Part 2 → Part 3 flow, and the constant
"swap two numbers" rebinding, with a cover page and roomy single-column fill-in boxes.

## Where the durable knowledge lives

The workbook's design — what it is, the numbered-peg / constant-swap method, and how it differs from
the `byhand*` book — is recorded in `tasks/reference/architecture-overview.md` (the `workbook/`
bullet). This task doc is the lean work record that points there.

## Related

- `workbook/induction-workbook.tex`, `workbook/Makefile`.
- `tasks/archive/2026/09/16/redesign-induction-workbook-flow.md` — the layout/pedagogy refinement.
- `docs/source/byhand*.rst` — the worked-solution counterpart (I/T/G role labels).
