# Redesign the induction workbook's flow (top-to-bottom) and relabeling representation

**Status:** complete
**Completed:** 2026-09-16 — approved by the maintainer through three render iterations and committed
(final commit "made boxes bigger").
**Priority:** 5
**Difficulty:** 5

## The problem

The first `workbook/induction-workbook.tex` (built under
`tasks/archive/2026/09/16/latex-workbook-solve-1-5.md`) looked good but **read in the wrong order**:
Part 1 and Part 3 sat side by side with Part 2 below, so a student reading top-to-bottom hit Part 1,
Part 3, then Part 2. It also relabelled with I/T/G role letters, which the maintainer suspected was
not the clearest representation. The brief: make it flow straight down (Part 1 → Part 2 → Part 3),
easy to fill in and relabel, and make the "solving n teaches you n+1" pattern obvious — while keeping
the TikZ aesthetic.

The tension that shaped the design: side-by-side had been chosen to save vertical space, because
naively stacking the parts makes a page ~`2*(n−1)+1` move-rows tall — fine for small n, but n=5
(15+1+15 = 31 rows) blows past one page. So "just stack them" regressed page fit, and the redesign
had to solve flow *and* fit together.

## What was decided, and why

Benchmarking the CLI's `apply`-under-relabel (it prints a clean top-to-bottom table **recipe move →
rebinding key → rebound move**) surfaced the key realization: because every sheet solves the *same*
concrete task — **move n discs from peg 1 to peg 3** (peg 2 = spare) — the rebinding is a **constant
swap** at every level, not a per-n puzzle:

- **Part 1** (move top n−1 discs, peg 1 → peg 2): take each move on the n−1 sheet and **swap 2↔3**
  (leave 1). [key 1→1, 2→3, 3→2]
- **Part 3** (move n−1 discs, peg 2 → peg 3): **swap 1↔2** (leave 3). [key 1→2, 2→1, 3→3]

This was verified to reproduce the optimal solves (n=3 → `1→3,1→2,3→2,1→3,2→1,2→3,1→3`, equal to the
game's `WIN_3_OPTIMAL`). The design that followed:

- **Dropped I/T/G in favour of concrete numbered pegs 1/2/3** (peg 1 start, peg 3 goal, peg 2 spare).
  Both I/T/G role letters and geometric shapes (triangle/square/circle) were considered and rejected:
  numbered pegs make the rebinding a mechanical "swap two numbers" a novice can do cold, and *are* the
  visual pattern the maintainer wanted.
- **Top-to-bottom flow:** header + peg picture → Part 1 → Part 2 (one move, peg 1→3) → Part 3, each
  stacked full-width, so reading down the page is the move order.
- **A cover page** ("how to use", the three pegs, the big idea) so a total novice can start cold.
- Each part = a swap-key banner + one worked example + a numbered grid of blank `__ → __` rebound
  moves. Rows per n = 2^(n−1)−1 (n2:1, n3:3, n4:7, n5:15).

## What was built, and the iteration sequence

Rewrote `workbook/induction-workbook.tex` end-to-end. New TikZ helpers replaced the old
`\rebindbox`/`\pegstack` machinery: `\onepeg`/`\pegdiscs`/`\startgoal` (peg pictures), `\movegrid`
(numbered `__ → __` fill-in cells), `\partblock` (full-width stacked Part box). Pegs 1/2/3 each carry
one fixed colour throughout (blue/orange/green). All pages were rendered with `pdftoppm` and eyeballed
(pixels, not just exit codes — the TeX Live + `pdftoppm` toolchain is in the agent sandbox).

Three passes, each after rendering and (from revision 1 on) maintainer feedback:

1. **Initial rewrite** → 6 pages (cover + n=1..5), clean build, multi-column grids to fit large n on
   one page. Two defects the render exposed were fixed: the cover's right-hand swap box overflowed the
   right margin (reanchored to `$(p1swap.north east)+(0.5,0)$`, using the already-loaded `calc` lib);
   and singular/plural — added `\discw`/`\movew` helpers so the n=1/n=2 sheets read "1 disc"/"1 move",
   rewording "…moves that carry…" → "…moves needed to carry…" to dodge subject-verb agreement at
   count 1.
2. **Revision 1 (maintainer: roomier, aligned boxes; prose dedup).** Rewrote `\movegrid` to a single
   vertical column, one box-pair per row (0.8×0.6cm), dropping the multi-column layout and the column
   argument from `\partblock`/`\hanoipage`; large n now runs onto a second page on purpose (the
   maintainer OK'd "don't mind wasting space vertically"). Added a `\dbox` helper for the base-case and
   Part 2 boxes (also removing four copies of an inline tikz draw). Trimmed the per-sheet header
   (dropped "Move N discs from peg 1 to peg 3", already shown by the subtitle + start→goal picture) and
   shortened Part 3's instruction ("Copy each move from your n=N sheet again" → "Copy them again").
3. **Revision 2 (maintainer: double the box size).** `\movegrid` cells to 1.6×1.2cm on a 1.5cm pitch,
   `\dbox` to 1.4×1.2cm. Verified no overfull boxes and no clipping — even n=5's 15-row grid fits one
   page inside its frame. Final booklet: 11 pages (large n spreads Part 1/Part 3 onto their own pages).

## Where the durable knowledge lives

The shipped workbook's design (numbered pegs, top-to-bottom flow, the constant-swap rebinding, and how
it differs from the `byhand*` book) is recorded in `tasks/reference/architecture-overview.md` (the
`workbook/` bullet).

## Related

- `workbook/induction-workbook.tex`, `workbook/Makefile`.
- `tasks/archive/2026/09/16/latex-workbook-solve-1-5.md` — the initial build this refined.
- `tasks/archive/2026/09/14/record-recipe-bindings-and-show-rebinding.md` — the three-panel
  (CLI/TUI/GUI) software view of the same rebinding.
- CLI: `python/src/hanoigame/hanoicli.py`; the shared rebinding table in `recipe.py`.
