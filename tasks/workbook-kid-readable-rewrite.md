# Kids' workbook: unique move names, a picture-led example, an answer key, and the page-2 picture bug

**Status:** in progress (reopened 2026-11-06 from `tasks/archive/2026/11/05/`)
**Priority:** 3
**Difficulty:** 4

## BLUF

`workbook/induction-workbook.tex` is the printable booklet that teaches a child to solve the Tower of
Hanoi by copying the previous sheet's answer and swapping peg numbers. A first-time reader could not
follow it: moves were called "old move k" / "new move m", and those names changed meaning from sheet
to sheet. This round gives every move one fixed name ("Sheet 2, move 3"), replaces the worked-example
page with a picture-led walkthrough of Sheet 2, adds an answer key at the back, and fixes the "big
idea" pictures on page 2. Done means the maintainer approves a printed build.

## Context (read first)

- The booklet's current design and why: the workbook bullet in `tasks/reference/architecture-overview.md`;
  earlier decisions in `tasks/archive/2026/09/16/redesign-induction-workbook-flow.md` (numbered pegs,
  top-to-bottom flow, big boxes) and `tasks/archive/2026/09/16/latex-workbook-solve-1-5.md`.
- Build: `make -C workbook` (pdflatex + TikZ). To check by eye, build in a scratch dir and render
  pages with `pdftoppm -r 60 -png`; zoom with `-r 200 -x -y -W -H`.
- The method: every sheet n moves n discs from peg 1 to peg 3. Step A copies Sheet n−1 with key
  1→1, 2→3, 3→2; Step B moves disc n from 1 to 3; Step C copies Sheet n−1 again with key
  1→2, 2→1, 3→3. The game does the same with `relabel 1 3 2` / `apply` / `relabel 2 1 3` / `apply`.
- 3-disc answer (to check pictures and the key): 1→3, 1→2, 3→2, 1→3, 2→1, 2→3, 1→3.
- Sheet 8 and beyond: shelved separately, `tasks/archive/2026/11/05/workbook-extend-to-8-discs.md`.

## The maintainer's review (William Emerison Six <billsix@gmail.com>, 2026-11-06)

- Page 1 (cover): keep as is.
- Page 2 ("the big idea", "how to swap", "how to use"): good, but may change to fit the fixes below.
  One of its pictures prints "4" outside its disc.
- Page 3 (worked example, Sheet 3 from Sheet 2): does not help someone new.
- Main problem: "old move 1" / "new move" are unclear to a new reader. On Sheet 3 the text says "find
  old move 1", but there are three moves to copy and it doesn't say where to find them. "Old" and
  "new" change meaning from sheet to sheet. Each cell should have a clearer label, unique if possible.

## Findings (agent's read of the source and the rendered PDF, 2026-11-06)

1. **Page-2 picture bug.** The four "big idea" pictures are TikZ pictures nested inside positioned
   nodes (`right=0.3cm of s`, `below=0.3cm of s`). The nested pictures inherit that positioning, so
   every disc number and peg label shifts. In picture B every number drops one disc ("4" sits under
   the base line, peg 2's top disc is blank); A and C shift right. The start picture is unpositioned,
   so it is correct. The sheets' own pictures are unpositioned and correct. Fix: don't nest pictures
   inside positioned nodes.
2. **Page 3 doesn't teach:** it has no discs (18 boxes of digits), starts at 3 rows per step instead
   of 1, and uses the old/new labels before the reader has seen a sheet.
3. **Move names:**
   - The same move has two names: Sheet 3's "new move 5" is Sheet 4's "old move 5".
   - A sheet's moves are written in three places (the Step A grid, the Step B box, the Step C grid),
     and "find old move 1" doesn't say which.
   - Some fixed text doesn't fit the sheet: Sheet 2 says "then old move 2, then old move 3", but it
     has one row. The examples say "Sheet 2 says 1 → 3" without saying which move.
4. Minor: in the Step B pictures the peg tops touch the caption above them.

## Decisions

All by William Emerison Six <billsix@gmail.com>, 2026-11-06:

- **Every move has one name, written out in full: "Sheet N, move K".** It is printed where the move is
  written and wherever it is copied, so "old" and "new" leave the booklet. Each box gets a small
  **from** / **to** label, so every box has a unique name (move name + from/to).
- **Page 3 becomes a picture-led walkthrough of making Sheet 2 from Sheet 1**: one copy row per step,
  the swap shown, and a picture of the discs after each move.
- **An answer key goes on the last pages of the PDF**, using the same move names as the rest of the
  booklet so a reader can match any move to its answer. The booklet mentions the answer key at the
  start.
- Unarchive this task and record the work here (rather than a new task).

## Plan

- [x] `git mv` this doc back from the archive; record the review, findings and decisions.
- [x] Fix the page-2 pictures: laid out in a `tabular`, no positioned nodes. A comment at
      `\drawpeg` warns against nesting.
- [x] Move names (`\mv{N}{K}`) on every row label, instruction, example, Sheet 1's box, Step B's
      box and the grown-ups page. "Old"/"new" no longer appear. Column headings are "COPY the move
      from Sheet N−1" and "SWAP and WRITE the move for Sheet N".
- [x] A small "from"/"to" tag in each box's top-left corner (`\cellbox`). It sits inside the box,
      so the 1.42 cm row pitch and Sheet 5's one-page 15-row grid are unchanged.
- [x] Page 2: new "Every move has a name" section; "How to use" item 5 names the answer key.
      Page 2's headings use a tighter `\head` so it still fits on one page.
- [x] Page 3 is now "Example: making Sheet 2 from Sheet 1": the start picture, then one row per
      step, each with the key spelled out and a disc picture after the move.
- [x] Each sheet n ≥ 3 says where the previous sheet's moves are ("on your Sheet 3, moves 1 to 3
      are in Step A, move 4 is in Step B, and moves 5 to 7 are in Step C").
- [x] Answer key after the grown-ups page, before the cut-out discs: every row of Sheets 1–5, each
      showing "copy Sheet N−1, move K: a→b  swap → Sheet N, move M: c→d". Each sheet's key starts
      a new page unless it fits (plain-TeX `\keeptogether`; `needspace` is not assumed in the book
      image). Rows generated by `tasks/adhoc/workbook-kid-readable-rewrite/gen_answer_key.py`, which
      replays every sheet on a simulated board (legal moves, all discs on peg 3, 2^n−1 moves); its
      3-disc output equals the game's optimal solve.
- [x] Fixed text that didn't fit small sheets: Sheet 2 says "There is only one row"; examples are
      phrased "if you copied 1 → 3" instead of quoting a particular move.
- [x] Step B pictures have 14 pt more room under their caption.
- [x] Build: `make -C workbook` exit 0, 0 errors, 0 overfull boxes, 21 pages. Every page was
      rendered with `pdftoppm` and checked by eye; page 2's pictures were checked at 150 dpi.
- [x] Updated the workbook bullet in `tasks/reference/architecture-overview.md` and the link in
      `tasks/archive/2026/11/05/workbook-extend-to-8-discs.md`.
- [ ] Maintainer reviews the print.
- [ ] Settle open question 1 (per-sheet fill-in list). This blocks archiving.
- [ ] Done-record rewrite → archive; `git rm` the adhoc generator in the archive commit.

Page order now: 1 cover, 2 big idea / swap / names / how to use, 3 example, 4 Sheet 1, 5–6 Sheet 2,
7–8 Sheet 3, 9–11 Sheet 4, 12–16 Sheet 5, 17 grown-ups, 18–20 answer key, 21 cut-out discs.

## Open questions

1. Besides the answer key at the back, should each sheet also end with a fill-in list of its own
   moves? Asked 2026-11-06; the answer ("3 yes, but the answer key for each should be the last
   pages") was read as "a printed answer key at the back". No per-sheet fill-in list was added.
   The maintainer said "not yet" (William Emerison Six <billsix@gmail.com>, 2026-11-06). It stays
   an open option and **must be settled before this task is archived**. The maintainer is
   reviewing the print first. Trade-off: a fill-in list gives the next sheet one place to copy
   from, but it adds one more copy where mistakes can creep in. The move names already say where
   each move is.

## History: the 2026-11-05 rewrite (the previous round of this task)

The booklet was rewritten at a fifth-grade reading level (approved 2026-11-05). Copy rows became COPY
boxes → swap arrow → NEW boxes, the paper form of the game's Recipe | Rebinding | Rebound view
(`tasks/reference/feature-spec.md` §4.8). New moves were numbered 1..2^n−1 through Steps A, B and C.
Added: a cover with step pictures and both swap keys, the change-it-twice warning, a worked example
(Sheet 3 from Sheet 2), a grown-ups page mapping each step to `hanoi-cli` commands, cut-out discs and
a peg mat, 12pt sans-serif text. `enumitem` was dropped (not shipped in the sandbox or book image).
The four `workbook/hanoi1..4.svg` worksheets were deleted: their colours didn't match, their boxes
were coloured by the unswapped numbers, their wording led to the change-it-twice trap, and their text
was converted to paths. The CLI survey behind it: under `relabel 1 3 2` / `apply solve-(n-1)` /
`relabel 1 2 3` / `1 -> 3` / `relabel 2 1 3` / `apply solve-(n-1)` the game wins n=2..5 in 2^n−1
moves.
