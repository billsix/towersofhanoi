# Redesign the induction workbook's flow (top-to-bottom) and relabeling representation

**Status:** proposed — needs go-ahead
**Priority:** 5
**Difficulty:** 5

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

- [ ] Run the CLI n=1..5; write down what makes its flow good (order, minimal decoding).
- [ ] Prototype a **top-to-bottom** page (Part 1 → Part 2 → Part 3 in reading order) and check n=5
      still fits reasonably (or paginate deliberately).
- [ ] Prototype the **shapes** relabeling (triangle/square/circle) vs the current I/T/G; render both.
- [ ] Pick the clearest combination; keep the existing visual polish (peg diagrams, framing).
- [ ] Rebuild + render all 5 pages (`pdflatex` + `pdftoppm`); confirm the flow reads straight down and
      the relabeling is easy to perform by hand. Aesthetics stay good.

## Notes

- The agent CAN build/render this itself (TeX Live + `pdftoppm` are in the agent sandbox — verify
  pixels, not just exit codes), unlike the wx GUI. So iterate on the actual rendered pages.

## Related

- `workbook/induction-workbook.tex`, `workbook/Makefile`.
- `tasks/latex-workbook-solve-1-5.md` (initial build).
- CLI: `python/src/hanoigame/hanoicli.py`; the shared rebinding table in `recipe.py`.
