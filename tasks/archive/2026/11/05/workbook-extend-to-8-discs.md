# Extend the kids' workbook from 5 discs to 8

**Status:** shelved, not done. The maintainer put it on hold after the first discussion, and it was
archived unstarted on 2026-11-05. To revive it, `git mv` it back to `tasks/` and answer the open
questions.
**Priority:** 9
**Difficulty:** 4

## BLUF

Add sheets 6, 7 and 8 to `workbook/induction-workbook.tex`. Sheet n has 2^n−1 moves, so this adds 445
moves and about 31 pages. Done means the maintainer approves a printed version that uses the layout
picked below.

## Context

- Read first: the workbook bullet in `tasks/reference/architecture-overview.md`, and the rewrite record
  `tasks/archive/2026/11/06/workbook-kid-readable-rewrite.md`. The booklet's current shape: numbered
  pegs, Steps A/B/C, COPY → swap → NEW rows, big boxes.
- Each sheet is one `\hanoipage{n}{2^(n-1)-1}` call, so adding a sheet is mostly mechanical. The
  pictures and fixed text are not (see below).

## Size

| Sheet | Copy rows (Step A + Step C) | New moves | Pages at today's box size | Child's time (~20 s/row) |
|---|---|---|---|---|
| 6 | 62 | 63 | ~5 | ~20 min |
| 7 | 126 | 127 | ~9 | ~40 min |
| 8 | 254 | 255 | ~17 | ~85 min |

## Changes needed whatever layout is picked

- **Disc pictures:** `\drawstack`/`\drawpeg` use a fixed disc height and width. Eight discs overflow the
  peg (too tall) and the peg spacing (too wide). The pictures need to scale with n.
- **Fixed text:** the cover says "five discs". The cut-out page needs 8 discs, probably on their own page.
  Sheet 5's "you finished the booklet" line must move. The grown-ups move-count list gains 63, 127, 255.
- **Finding your place:** a 127-row grid spans about 8 pages. Each page needs a header like "Sheet 7,
  Step A, old moves 33–48".

## Open questions (from the 2026-11-05 discussion; unanswered)

1. Layout: (a) one booklet with sheets 1–8 (~49 pages); (b) two booklets from the same `.tex`: Book 1 is
   sheets 1–5, unchanged; Book 2 is sheets 6–8 plus a one-page refresher; or (c) smaller boxes for
   sheets 6–8. Recommendation: (b). Most children stop at 5, and (c) undoes the earlier "make the boxes
   bigger" decision.
2. For sheets 6–8, keep the COPY boxes or print NEW boxes only? NEW-only halves the writing, but then a
   mistake can't be traced to the copy or the swap. Recommendation: keep COPY.
