# Redesign the induction workbook's flow (top-to-bottom) and relabeling representation

**Status:** complete
**Completed:** 2026-09-16 — approved by the maintainer through three render iterations and committed
(final commit "made boxes bigger"). See "Design decided" and "Iteration log".
**Priority:** 5
**Difficulty:** 5

## Design decided (2026-09-15)

Studied the CLI benchmark: its `apply`-under-relabel prints a top-to-bottom table **recipe move →
rebinding key → rebound move**. The key realization that reshapes the whole workbook: because every
sheet solves the *same* concrete task — **move n discs from peg 1 to peg 3** (peg 2 = spare) — the
rebinding is a **constant swap** at every level, not a per-n puzzle:

- **Part 1** (move top n−1 discs, peg 1 → peg 2): take each move on your n−1 sheet and **swap 2↔3**
  (leave 1). [key 1→1, 2→3, 3→2]
- **Part 3** (move n−1 discs, peg 2 → peg 3): **swap 1↔2** (leave 3). [key 1→2, 2→1, 3→3]

Verified this reproduces the optimal solves (n=3 → `1→3,1→2,3→2,1→3,2→1,2→3,1→3`, == the game's
`WIN_3_OPTIMAL`). So the redesign:

- **Drop I/T/G** in favour of **concrete numbered pegs 1/2/3** (peg 1 start, peg 3 goal, peg 2 spare)
  — this is what "use the forms to move the real pieces" needs, and it makes the rebinding "swap two
  numbers", which a novice can do mechanically. (Tried framing against I/T/G and shapes; the constant
  numeric swap is clearest and *is* the visual pattern the maintainer wanted.)
- **Top-to-bottom flow:** header + peg picture → Part 1 → Part 2 (one move, peg 1→3) → Part 3, each
  stacked full-width, so reading down the page *is* the move order and copying it onto the next sheet
  is trivial.
- **A cover page** ("how to use", the 3 pegs, the big idea) so a total novice can start cold.
- Each part = a swap-key banner + one worked example + a compact numbered grid of blank `__ → __`
  rebound moves (multi-column for n=4,5 to fit the page). The student reads each move off their n−1
  sheet, applies the swap, writes the actual move here, then does it.
- Rows per n = 2^(n−1)−1 (n2:1, n3:3, n4:7, n5:15).

## Iteration log (2026-09-15)

Rewrote `workbook/induction-workbook.tex` end-to-end to the "Design decided" plan. Result: 6 pages
(cover + one sheet per n=1..5), builds clean with `pdflatex` (0 overfull boxes), all rendered and
eyeballed at 110 dpi.

- **Numbered pegs 1/2/3 with one fixed colour each** (blue/orange/green), replacing the I/T/G roles
  and the `\rebindbox`/`\pegstack` machinery. New helpers: `\onepeg`/`\pegdiscs`/`\startgoal` (peg
  pictures), `\movegrid{rows}{cols}` (numbered `__ → __` cells, fills column-by-column), `\partblock`
  (full-width stacked Part box).
- **Top-to-bottom flow:** each sheet is header + start→goal picture, then Part 1 (peg 1→2, swap 2↔3)
  → Part 2 (biggest disc, one move 1→3) → Part 3 (peg 2→3, swap 1↔2), each full-width and stacked, so
  reading down the page *is* the move order. n=4 (7 rows, 2 cols) and n=5 (15 rows, 3 cols) still fit
  one page each.
- **Cover page** added: puzzle statement + big picture, the three-part trick, the two constant swap
  keys side by side, and a numbered "how to use" list.
- **Fixes after first render:** (1) the cover's right-hand swap box overflowed the right margin —
  reanchored it to `$(p1swap.north east)+(0.5,0)$` (needs the already-loaded `calc` lib) so the two
  7.6cm boxes sit within the text block; (2) singular/plural — added `\discw`/`\movew` helpers so the
  n=1/n=2 sheets read "1 disc"/"1 move", and reworded "…moves that carry…" → "…moves needed to
  carry…" to dodge subject-verb agreement at count 1.

**Revision (2026-09-15, maintainer feedback):** (1) roomier draw-boxes, all in a single vertical
column — `\movegrid` rewritten to one box-pair per row (0.8×0.6cm, 0.9cm pitch), dropping the
multi-column layout; `\partblock`/`\hanoipage` lost their column argument. Large n now runs onto a
second page on purpose (8 pages total: n=4 and n=5 each spill Part 3 to a second page), which the
maintainer OK'd ("don't mind wasting space vertically"). New `\dbox` helper gives the base-case and
Part 2 the same roomy box and removes four copies of an inline tikz draw. (2) Prose dedup: trimmed
the per-sheet header (dropped "Move N discs from peg 1 to peg 3", already shown by the subtitle +
start→goal picture; header now carries only the disc-stacking rule + print note) and shortened Part
3's instruction ("Copy each move from your n=N sheet again" → "Copy them again", since Part 1 already
said where to copy from). Subtitle now uses `\discw` too, so n=1 reads "1 disc".

**Revision 2 (2026-09-15, maintainer feedback):** doubled the draw-box size for more writing room —
`\movegrid` cells are now 1.6×1.2cm on a 1.5cm pitch (was 0.8×0.6cm / 0.9cm), and `\dbox` (base
case + Part 2) is 1.4×1.2cm. Verified no overfull boxes and no clipping: even n=5's 15-row grid fits
one page inside its frame. Booklet is now 11 pages (large n spreads Part 1/Part 3 onto their own
pages — the accepted vertical-space trade).

Staged (not committed, per the maintainer's standing "I commit, you stage"): `workbook/induction-workbook.tex`
and this task doc. The rebuilt `workbook/induction-workbook.pdf` is a build artifact and is left
unstaged/untracked. **Remaining for the maintainer:** eyeball the printed pages; if good, commit
(and this task then archives in its own commit).

## BLUF

The `workbook/induction-workbook.tex` PDF looks good but **reads in the wrong order**: because Part 1
and Part 3 are side-by-side and Part 2 sits *below* them, a student reading top-to-bottom hits
Part 1, Part 3, then Part 2. Redesign it so it flows **straight down in order (Part 1 → Part 2 →
Part 3)**, is easy to fill in and relabel, and makes the "solving n teaches you n+1" pattern
obvious. **Experiment** with the relabeling representation — I/T/G may not be the clearest; try
geometric **shapes (triangle / square / circle)** so the pattern reads visually. Keep the current
aesthetic (the TikZ diagrams are nice) — fix the *flow* and the *relabeling clarity*. Benchmark the
target flow against the CLI (below), whose output reads cleanly top-to-bottom.

## Context — read first

- **Benchmark first — run the CLI for n = 1..5 and study its flow.** The command-line game presents
  the solve and the rebinding in a clean top-to-bottom order (the three-column table, then the step
  log). Drive it with scripted stdin, e.g.:
  ```python
  import io, sys
  from hanoigame.hanoicli import run

  run(io.StringIO("1\n...\n"), sys.stdout)  # solve n=1, then 2, 3, 4, 5; relabel; apply
  ```
  (from `python/`, `PYTHONPATH=src`). Note *why* it reads well — that's the flow to mirror on paper.
- **The artifact:** `workbook/induction-workbook.tex` (built via `pdflatex`, target in
  `workbook/Makefile`; render with `pdftoppm -png` to eyeball). Current structure per n page:
  start→goal peg diagram; induction-hypothesis text; then **Part 1 (move top n−1: I→T)** and
  **Part 3 (move n−1: T→G)** as two **side-by-side** grey blocks, each with an I/T/G "Rebind" box +
  a From/To copy grid; then **Part 2 (move disc n: I→G)** as a full-width box *below*. That
  side-by-side layout is what breaks top-to-bottom reading order.
- **Built under** `tasks/latex-workbook-solve-1-5.md` (the initial build); this task refines its
  layout/pedagogy. The three-panel *software* view (CLI/TUI/GUI) is the archived
  `tasks/archive/2026/09/14/record-recipe-bindings-and-show-rebinding.md`.

## The real tension to solve (why "experiment, figure it out")

Side-by-side was chosen to save vertical space: stacking Part 1 → Part 2 → Part 3 vertically makes a
page ~`2*(n−1)+1` move-rows tall — fine for n=2..3, but n=5 (15+1+15 = 31 rows) blows past one page.
So a naive "just stack them" regresses page fit. Options to explore:
- Stack the three parts top-to-bottom but make each **compact** (smaller boxes / two columns of
  boxes within a part), accepting multiple pages per large n if needed.
- Use **shapes instead of I/T/G**: draw each peg-role as a triangle/square/circle so "the n−1
  solution, relabelled" is a visual substitution the student *sees* rather than decodes from letters
  — this may cut the amount of written copying and tighten the layout.
- Reconsider whether every move must be hand-copied, or whether the shape-substitution makes the
  pattern clear with less repetition.
Decide empirically: build variants, render them, judge the flow + fit. I/T/G might still win — or
shapes might; the point is to try both.

## Plan

- [x] Run the CLI n=1..5; write down what makes its flow good (order, minimal decoding). → the
      recipe-move → key → rebound-move table reads top-to-bottom; captured in "Design decided".
- [x] Prototype a **top-to-bottom** page (Part 1 → Part 2 → Part 3 in reading order) and check n=5
      still fits reasonably. → done; n=5 fits one page via a 3-column grid.
- [x] Prototype the relabeling representation. → rejected I/T/G *and* shapes in favour of concrete
      numbered pegs 1/2/3 (the rebinding is then a constant "swap two numbers"); see "Design decided".
- [x] Pick the clearest combination; keep the existing visual polish (peg diagrams, framing).
- [x] Rebuild + render all 6 pages (`pdflatex` + `pdftoppm`); flow reads straight down, relabeling is a
      mechanical swap, 0 overfull boxes. Aesthetics preserved.

## Notes

- The agent CAN build/render this itself (TeX Live + `pdftoppm` are in the agent sandbox — verify
  pixels, not just exit codes), unlike the wx GUI. So iterate on the actual rendered pages.

## Related

- `workbook/induction-workbook.tex`, `workbook/Makefile`.
- `tasks/latex-workbook-solve-1-5.md` (initial build).
- CLI: `python/src/hanoigame/hanoicli.py`; the shared rebinding table in `recipe.py`.
