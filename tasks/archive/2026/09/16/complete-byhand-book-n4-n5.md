# Complete the by-hand book: finish the byhand4 stub and add byhand5

**Status:** complete
**Completed:** 2026-09-16
**Priority:** 5
**Difficulty:** 3
**Started:** 2026-09-16

## What this was

The Sphinx by-hand tutorial trailed off: `docs/source/byhand4.rst` was a 14-line stub (license + a
"Solve For 4" title, no content) and `byhand5.rst` did not exist, while `byhand1..3` were complete and
the new `workbook/induction-workbook.tex` already taught the same method for n=1..5. The task filled the
byhand4 stub and authored byhand5 so the book covers n=1..5 consistently, mirroring `byhand3`'s
structure, wired into the toctree and building cleanly. Surfaced as a follow-on to the workbook work
(archived `tasks/archive/2026/09/16/latex-workbook-solve-1-5.md` and `.../redesign-induction-workbook-flow.md`).

## What was decided, and why

- **Mirror `byhand3` exactly, keeping the I/T/G generalization** (maintainer, 2026-09-16). Each
  `byhandN` page carries four sections — `N-1to3` (the concrete solve), `N-ItoG` (its I/T/G
  generalization), and `N-1to2` / `N-2to3` (substitutions of `N-ItoG`). byhand4/5 replicate all four,
  so the I/T/G framing stays in the book; the numbered-peg-only framing lives in the workbook instead.
- **Generate the pages rather than hand-writing them.** byhand4 needed a 15-move table (2⁴−1) and
  byhand5 a 31-move table (2⁵−1), each in four orientations, plus ASCII start→goal art that had to be
  widened (byhand3's fixed 9-wide peg base cannot hold a 5-disc bottom disc). Hand-transcribing ~90
  move rows and scaling the art by eye was too error-prone, so a generator produced them
  correct-by-construction.

## What was built

- `docs/source/byhand4.rst` and `byhand5.rst`, each with the four sections above, their `:ref:`
  sub-problem link tables, From/To move tables, and ASCII diagrams — mirroring `byhand3`. `byhand5`
  was added to the `docs/source/index.rst` toctree.
- The structure follows the recursion the pages encode: N discs 1→3 = (N−1 discs 1→2) + (1 disc 1→3) +
  (N−1 discs 2→3). So byhand4's `4-1to3` reuses the existing `3-1to2`, `1-1to3`, `3-2to3`, and defines
  `4-1to3` / `4-1to2` / `4-2to3`; byhand5 reuses those `4-*` anchors.

## Verification

The move tables are correct-by-construction: the generator emits them from the standard optimal-Hanoi
recursion, and a self-check asserts its n=3 output matches `byhand3.rst`'s known-correct tables before
it writes (there are no `WIN_4/5` constants in the code — the recursion is the source of truth). The
book built clean (`sphinx-build -b html` in a `BUILD_DOCS=1` image): no undefined-`:ref:` warnings,
only the pre-existing unrelated `_static` warning; the n=5 ASCII art was eyeballed (widest disc fits
the widened base).

## The generator (durable)

`tools/gen_byhand.py` (promoted from `tasks/adhoc/` at archive; idempotent — rerunning writes identical
files) is the source of truth for byhand4/5 — regenerate, do not hand-edit. The base solve is
`solve(n,1,3)`; the three other orientations are digit remaps of it — `ItoG` = {1:I,2:T,3:G}, `1to2` =
swap 2↔3, `2to3` = swap 1↔2 — exactly the substitutions byhand3 documents in prose (and the same swaps
the workbook uses). ASCII base width scales as `2n+3`. A follow-on wired a drift guard:
`python/tests/test_byhand_drift.py` fails the pytest gate if byhand4/5 ever diverge from the generator.

## Where the durable knowledge lives

`tasks/reference/architecture-overview.md` — the `docs/source/` bullet records that byhand4/5 are
generated (not hand-edited), names `tools/gen_byhand.py`, and points at the drift test.
