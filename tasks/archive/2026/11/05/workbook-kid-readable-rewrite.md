# Rewrite the induction workbook for a fifth-grade reader; delete the SVG worksheets

**Completed:** 2026-11-05. The maintainer, William Emerison Six <billsix@gmail.com>, approved the
rewrite.

## Summary

`workbook/induction-workbook.tex` taught the right method ("solve small, relabel, replay"), but in adult
language and without saying *how* to copy and swap. It was rewritten at a fifth-grade reading level. Each
copy row became COPY boxes (the old sheet's move, unchanged) → a swap arrow → NEW boxes (the move after
the swap key). That is the paper version of the game's three-panel rebinding view (Recipe | Rebinding |
Rebound, `tasks/reference/feature-spec.md` §4.8). The four `workbook/hanoi1..4.svg` worksheets were
deleted. The rewrite kept the earlier design decisions: numbered pegs, top-to-bottom flow, and big boxes
(`tasks/archive/2026/09/16/redesign-induction-workbook-flow.md`). The current design is described in the
workbook bullet of `tasks/reference/architecture-overview.md`.

## What the UI shows for relabelling (surveyed from the Python CLI, the behaviour oracle)

- `relabel a b c` printed "Relabelled: physical pegs 1,2,3 now show as a,b,c." The board then showed two
  label rows: the current labels, and the physical 1 2 3 under them.
- `apply <recipe>` under a relabelling printed the Recipe | Rebinding | Rebound table, then "Done.".
- For a size-n solve the two relabels were always `relabel 1 3 2` (swap 2 and 3) and `relabel 2 1 3`
  (swap 1 and 2). These are the workbook's Step A and Step C keys, so paper and game agree.
- The sequence `relabel 1 3 2`, `apply solve-(n-1)`, `relabel 1 2 3`, `1 -> 3`, `relabel 2 1 3`,
  `apply solve-(n-1)` won n=2..5 at the optimal 2^n−1 moves. The 3-disc `history` matched the
  workbook's worked example (`1→3, 1→2, 3→2, 1→3, 2→1, 2→3, 1→3`).

## What was wrong with the old LaTeX workbook

1. Adult reading level: "induction", "relabelling", "carry"; long sentences joined with semicolons;
   math notation (`n−1`, `2^n−1`) in children's text.
2. Nowhere to copy into: the child read the old move, swapped it in their head, and wrote only the
   result. A mistake could not be traced back to the copy or the swap.
3. The swap was stated as a rule ("swap 2 and 3"), not a key to look up.
4. Nothing warned about the change-it-twice trap. A child who turns every 2 into a 3, then every 3 into
   a 2, ends up with all 2s.
5. No worked example of a whole sheet.
6. No pictures of the positions between start and goal.
7. Discs were not numbered, but the text said "disc n".
8. Move numbering restarted in each part, so the next sheet had to stitch three parts together.
9. A bug printed "your n = 3+1 sheet" (TeX did not do the sum).
10. "Print one copy per value of n" appeared on every page of a printed booklet.
11. No self-checks; no page for a grown-up; nothing to move with; small grey 11pt serif text.

## What was wrong with the SVGs (why they were deleted)

They used different colours from the workbook and the game (red/blue/green instead of blue/orange/green).
Their boxes were coloured by the old, unswapped numbers, which nudged a child to write the wrong ones.
They said "replace 2 with 3 and 3 with 2" (the change-it-twice trap). They had no peg numbers, discs, or
move numbers. Their text was converted to paths, so it could not be edited. Nothing linked to them.

## What was built

The new booklet (18 pages):

- **Cover:** what you need; the three rules; how to write a move; "the big idea" with pictures of the
  start, after Step A, after Step B, and after Step C; both swap keys and the change-it-twice warning;
  how to use the booklet.
- **Worked example:** Sheet 3 made from Sheet 2, every box filled in.
- **Sheets 1–5:** Step A (numbered Copy / Swap / Move instructions, the key, an example) → the COPY → swap
  → NEW grid → a "when Step A is done" picture → Step B → Step C (same grid, other key) → "Finished! Check
  your work". New moves are numbered 1..2^n−1 straight through Steps A, B and C, so the next sheet copies
  "old move 1, 2, …" by number.
- **For grown-ups:** why it works; checks (2^n−1 moves; first move 1→3 for odd n, 1→2 for even n); the
  game's command sequence and how its table columns match COPY / key / NEW.
- **Cut-out discs** 1–5 and a peg mat. 12pt sans-serif text.

Other changes:

- Dropped `enumitem`, because neither the sandbox nor the root book image ships it.
- Deleted `workbook/hanoi1..4.svg` and removed their Inkscape targets from `workbook/Makefile`.
- Updated the README, the `CLAUDE.md` layout line, and `tasks/reference/architecture-overview.md`.

Verification: `make -C workbook` built with 0 errors and 0 overfull boxes. Every page was rendered with
`pdftoppm` and checked by eye.

## Decisions

- Rewrite approved (William Emerison Six <billsix@gmail.com>, 2026-11-05).
- SVGs deleted rather than redrawn or kept (William Emerison Six <billsix@gmail.com>, 2026-11-05).
- Extending to 8 discs was discussed and put on hold. The analysis and options were shelved, unstarted, in
  `tasks/archive/2026/11/05/workbook-extend-to-8-discs.md`.
