# Trim hanoi's CLAUDE.md (5,851 B ≈ 1.5K tok, loaded every session)

**Status:** Done — trimmed 2026-09-13 (pending archive after the work commit)
**Priority:** 6
**Difficulty:** 2

## Result (2026-09-13)
`CLAUDE.md` **5,851 B → 3,349 B** (−2,502 B). Moved verbatim to
`tasks/reference/architecture-overview.md`: the whole "Module map (teaching intent per file)"
section and the doc/roadmap history (archived `PLAN.md`/`NOTES.md`, the reverted OpenGL step,
the descoped optional follow-ons). Left a one-line pointer in the Documentation-model /
reference-docs note. Trimmed: the "Documentation model" block to a lean 2-line note; the
"Status" section condensed (bash/book/worksheet triple → one line pointing at Layout, keeping
the front-end inventory + 72-test count); and the redundant 2026-08-27 in-flight-tasks
listing dropped in favour of the session-start `tasks/` scan. arch-overview.md grew
2,894 B → 5,250 B.

## BLUF
hanoi's `CLAUDE.md` is 5,851 B and re-spliced into the AI's context every session/turn.
It is mostly operational and healthy, but the **Module map (teaching intent per file)**
section largely duplicates the **Layout** section while adding deep per-file teaching
rationale, and the **Documentation model** / **Optional follow-ons** blocks carry project
history (archived PLAN.md/NOTES.md, the reverted OpenGL step). Move the deep/durable
detail into `tasks/reference/architecture-overview.md` (which already exists) and trim the
history, keeping CLAUDE.md a lean operational reference.

## Context
- Why: `CLAUDE.md` loads on every session/turn. Method + numbers:
  runCrushInContainer `tasks/reference/crush-context-assembly.md` (measured 2026-09-13:
  geometricalgebra's 74,732 B CLAUDE.md cost ~18,683 tok/turn ≈ 47% of Crush's system
  prompt). hanoi is far smaller (~1.5K tok) but past the ~5 KB lean line, with clear
  redundancy and history to relocate.
- Current size: 5,851 B. @-imports: none.
- Existing reference docs: `tasks/reference/architecture-overview.md` (dispatch data-flow
  across the three frontends + the default-label-space recipe invariant) — the natural
  home for the moved teaching-intent detail.
- Convention: CLAUDE.md stays lean and operational; durable rationale/history/deep
  mechanics move to `tasks/reference/<slug>.md`.

## Stay vs move (section-by-section)
| section | ~bytes | Verdict | Destination |
|---|---|---|---|
| `# hanoi` intro ("teaching project" / solve-relabel-replay) | ~450 | STAY | CLAUDE.md |
| `## Status` (package, 3 front-ends, bash demos, book, worksheets, 72 tests) | ~1050 | TRIM | condense — much overlaps Layout; keep the one-line inventory + test count |
| `## Layout` | ~750 | STAY | CLAUDE.md |
| `## Build / container workflow` | ~700 | STAY | CLAUDE.md |
| `## Conventions` (ruff; thin front-ends; label-space recipe invariant) | ~600 | STAY | CLAUDE.md |
| `## Module map (teaching intent per file)` | ~1700 | MOVE | `tasks/reference/architecture-overview.md` — per-file teaching intent (hanoirecursive/iterative, bash pipeline pedagogy, docs/workbook); duplicates Layout, leave a one-line pointer |
| `## Documentation model` (README vs CLAUDE; PLAN.md/NOTES.md archived; OpenGL attempted+reverted) | ~700 | TRIM/MOVE | keep 2-line doc-model note in CLAUDE.md; move the archival/OpenGL history to a reference doc or the archived roadmap |
| In-flight tasks block (2026-08-27 listing) | ~350 | TRIM | redundant with the session-start `tasks/` scan; drop or reduce to a pointer |
| Reference docs pointer | ~300 | STAY | CLAUDE.md |
| Optional follow-ons (descoped roadmap) | ~250 | MOVE | reference doc / archived roadmap — historical descope, not operational |

## Projected result / Related
- Projected CLAUDE.md: ~3.5–4 KB (intro + trimmed Status + Layout + Build + Conventions +
  lean doc-model + reference pointers). Teaching-intent-per-file and history live in
  `tasks/reference/`.
- runCrushInContainer `tasks/reference/crush-context-assembly.md` — measurement + method.
