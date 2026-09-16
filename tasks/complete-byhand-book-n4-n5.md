# Complete the by-hand book: finish the byhand4 stub and add byhand5

**Status:** proposed — needs go-ahead
**Priority:** 5
**Difficulty:** 3
**Started:** 2026-09-16

## BLUF

The Sphinx book's by-hand tutorial trails off: `docs/source/byhand4.rst` is a 14-line stub (license +
a "Solve For 4" title, no content) and `byhand5.rst` does not exist — while `byhand1..3` are complete
and the new `workbook/induction-workbook.tex` already teaches the same method for n=1..5. Done = the
byhand4 stub is filled and byhand5 is authored, both mirroring byhand3's structure, wired into the
toctree, building cleanly with no Sphinx cross-reference warnings, and with correct move tables.

## Context — read first

- **The template — `docs/source/byhand3.rst`** (the complete n=3 page; mirror its structure exactly).
  Each `byhandN.rst` has a "Solve For N" title and, per orientation, a section that carries: a labelled
  anchor (`.. _N-1to3:` etc.), a **table of `:ref:` links** to the smaller sub-problems it reuses, the
  resulting **From/To move table**, and an **ASCII start→goal diagram**. Also read `byhand1.rst` /
  `byhand2.rst` for the anchor conventions, and `docs/source/index.rst` for the toctree.
- **Current state (verified 2026-09-16):**
  - Line counts: `byhand1` 89, `byhand2` 144, `byhand3` 178 (complete); **`byhand4` 14 (stub)**;
    **`byhand5` absent**.
  - `docs/source/index.rst` toctree (lines 19–22) lists `byhand1..byhand4`; **byhand5 is not listed**.
  - Anchors defined today: `byhand1` → `1-1to3`, `1-1to2`, `1-2to3`; `byhand2` → `2-1to3`, `2-1to2`,
    `2-2to3`; `byhand3` → `3-1to3`, `3-1to2`, `3-2to3`, **plus an I/T/G generalization `3-ItoG`**.
- **The recursion the pages encode:** moving N discs 1→3 = (N−1 discs **1→2**) + (1 disc **1→3**) +
  (N−1 discs **2→3**). So:
  - **byhand4** "From 1 to 3" references `3-1to2`, `1-1to3`, `3-2to3` (**all already exist**). byhand4
    must **define** `4-1to3`, `4-1to2`, `4-2to3` so byhand5 can link to them.
  - **byhand5** "From 1 to 3" references `4-1to2`, `1-1to3`, `4-2to3` (which byhand4 will define).
  - Move counts: byhand4 = **15** moves (2⁴−1), byhand5 = **31** moves (2⁵−1).
- **Correctness check available:** the game encodes the optimal solves — cross-check the hand-authored
  From/To tables against `WIN_4`/`WIN_5` (see `python/src/hanoigame/recipe.py` / the model), or generate
  them with `bash/hanoin.sh`. Don't transcribe 15/31 moves by eye alone.
- **Related recent work (same method, done):** the fill-in workbook — archived
  `tasks/archive/2026/09/16/latex-workbook-solve-1-5.md` and `.../redesign-induction-workbook-flow.md`.
  The book and workbook should tell the same n=1..5 story; this task closes the book's half.
- **Building the book needs `BUILD_DOCS=1`** — nested, that means `make docs BUILD_DOCS=1` (the
  lean-image default drops the docs toolchain when nested; see
  `tasks/archive/2026/09/16/minimal-nested-image.md`).

## Goal

Complete the Sphinx by-hand tutorial so it covers n=1..5 consistently: fill the `byhand4` stub and
author `byhand5`, mirroring `byhand3`'s structure (labelled anchors, `:ref:` sub-problem link tables,
From/To move tables, ASCII diagrams), wired into the toctree and building cleanly.

## Plan

- [ ] Fill `byhand4.rst` mirroring `byhand3`: define `4-1to3` / `4-1to2` / `4-2to3` (+ `4-ItoG` per Q1),
      each with its `:ref:` sub-problem table, correct From/To table (15 moves for 1→3), and ASCII
      diagram.
- [ ] Author `byhand5.rst` likewise: `5-1to3` (31 moves) / `5-1to2` / `5-2to3` (+ `5-ItoG` per Q1).
- [ ] Add `byhand5` to the `docs/source/index.rst` toctree after `byhand4`.
- [ ] Verify every move table against the game's optimal solve (`WIN_4`/`WIN_5`) or `bash/hanoin.sh`.
- [ ] Build the book (`make docs BUILD_DOCS=1`) and confirm no undefined-`:ref:` warnings and that
      byhand4/5 render.

## Notes / decisions

- `byhand3`'s move tables already use **concrete numbered pegs (1/2/3)** — the same notation the
  workbook adopted — so there's no I/T/G-vs-numbered choice for the numbered orientation sections; just
  follow byhand3.
- `byhand3` additionally carries an I/T/G generalization section (`3-ItoG`); whether byhand4/5 replicate
  that is Q1.

## Open questions

1. **Mirror `byhand3`'s full section set — including an `N-ItoG` I/T/G generalization — in byhand4/5,
   or only the three numbered-peg orientations (`N-1to3`/`1to2`/`2to3`) the cross-references need?**
   Recommendation: mirror byhand3 exactly (include `4-ItoG`/`5-ItoG`) for consistency across the book —
   unless you're deliberately phasing out the I/T/G framing in favour of the numbered-peg approach the
   workbook adopted, in which case byhand4/5 stay numbered-only (and byhand2/3's I/T/G sections become a
   separate cleanup). Which?
