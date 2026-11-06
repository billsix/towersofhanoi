# Apply the 2026-11-06 naming and scope rules across hanoi (the Python package under `python/`)

**Status:** proposed — needs go-ahead (open questions below)
**Priority:** 5
**Difficulty:** 4
**Created:** 2026-11-06 (William Emerison Six <billsix@gmail.com>): asked for the geometricalgebra survey
task ("search through all of geometricalgebra and see if there is programming advice that we added that
should be applied to the codebase, to refactor it"), then "add a similar task to every other python
project in opt".

## BLUF

Five naming and scope rules were added to the shared Python standard on 2026-11-06, while refactoring
geometricalgebra. This task searches this project's Python for places that break them, records every
candidate in a worklog, and refactors the ones that should change, with no change in behaviour. Done =
every candidate is either refactored or recorded as left alone with its reason, and the gates pass
(containerized `make test`, `make type-check`, and `make format` from `python/`).

## Context (read first)

- **The rules**, in the shared `python-coding-standard.md` (github.com/billsix/runClaudeInContainer
  `tasks/reference/`; mounted at `~/.claude/reference/`), sections "Inline a value used once, and name
  it in a comment instead of a binding" and "What earns an extraction"; the language-agnostic summary is
  `code-style-conventions.md`, "Names: inline what is used once, declare at the point of use, nest and
  shadow":
  1. **Inline a binding used once**, even one that exists to explain the expression; put a comment above
     the inlined subexpression that describes it and gives it its name.
  2. **Two uses do not automatically earn a name**: check whether one expression absorbs them (e.g.
     `getattr(obj, name, fallback)` or `d.get(key, default)` in place of a `None` check plus ternary), or
     whether a cheap expression can be repeated. Keep the name when repeating the expression reads worse
     or recomputes something expensive.
  3. **Declare a name at the point of use**, not many lines earlier.
  4. **Nest a helper with one caller inside that caller.**
  5. **When nesting, shadow deliberately**: the helper's parameter takes the caller's name when it means
     the same thing, and the shadowing is verified (the helper never needs the outer value; none of its
     other names hide an enclosing binding).
- **The worked example to imitate:** github.com/billsix/geometricalgebra
  `tasks/reference/python-coding-standard-gacalc.md`, "Inline once, declare at use, nest and shadow"
  (the 2026-11-06 refactor of `Frame.to_invertible_function`). The same survey for that project is its
  `tasks/apply-2026-11-06-naming-and-scope-rules.md`.
- **Rules that compete with these, and win:** an externally-defined name (a framework override, a
  callback signature, a dunder) is never renamed; "annotate every binding" still applies to every name
  that survives; a public parameter name is part of the API and is out of scope.

## Scope

- **In:** `python/src/` and `python/tests/` (the Python package; its own `python/CLAUDE.md` and
  `python/Makefile`).
- **Out:** the Rust and C++ ports (`rust/`, `cpp/`; other languages, separate surveys if wanted), and the
  vendored Emacs trees.

## Project constraints (these override the rules where they conflict)

- **The Python package is the behaviour oracle for the Rust/C++ ports** (`python/CLAUDE.md`,
  "Conventions"). Refactors must not change behaviour; where a port deliberately mirrors the Python
  structure, note any structural change that makes the port read differently, rather than changing the
  port in this task.
- **Tests are doctests by default**, with typed bindings in the examples. A name bound in a doctest to
  show the reader a step is documentation, not a local to inline.
- Line length 80, fully typed, Google docstrings (`python/CLAUDE.md`).

## Plan

1. **Discover with a script, not by reading every file.** Write
   `tasks/adhoc/apply-2026-11-06-naming-and-scope-rules/discover.py`, an `ast` walk over the in-scope paths (repo-relative paths, derived
   from the script's own location) that reports:
   - a local assigned once and loaded once (rule 1), with the line distance between the two (rule 3);
   - a local assigned once and loaded exactly twice, flagged for a look (rule 2);
   - a local whose first load is far from its assignment, e.g. more than 10 lines (rule 3);
   - a module-level or enclosing-scope function called from exactly one function and not imported by a
     test (rule 4);
   - a nested function whose parameter names differ from an enclosing local holding the same kind of
     value, as a lead for rule 5 (a judgment call, so a lead only).
   Write the results to `tasks/adhoc/apply-2026-11-06-naming-and-scope-rules/data/candidates.txt` (a committed snapshot worklog). If the
   geometricalgebra survey has already produced its `discover.py`, copy it and adjust the paths rather
   than rewriting it.
2. **Triage the worklog** into: refactor; leave alone (with the reason, e.g. a loop accumulator, a
   binding a doctest or notebook shows the reader, a name a test asserts on, a public parameter, an
   annotation that carries information the inline form would lose, or a project constraint above); and
   ask the maintainer. Record the counts here.
3. **Refactor in small batches, one module (or a few related ones) at a time**, matching the worked
   example: inline with a naming comment, absorb double uses, move declarations down, nest one-caller
   helpers and verify the shadowing. Run ruff and `ty` after each batch.
4. **Gates:** containerized `make test`, `make type-check`, and `make format` from `python/`.
5. Record what was changed, what was left alone and why, and any rule the survey showed needs a sharper
   wording; feed that back to the shared standard (github.com/billsix/runClaudeInContainer, mirrored in
   github.com/billsix/runCrushInContainer).

## Open questions

1. **Survey first, or survey and apply?** (a) Run the discovery and triage, then stop and show the
   maintainer the worklog before any refactor, or (b) apply the clear cases straight away and bring only
   the judgment calls. Recommended: follow whatever the maintainer decides for the geometricalgebra
   survey (its open question 1); if this task runs first, (a) for the first module, then (b).
2. **A one-caller helper that a test imports:** counts as having a second caller and stays at module
   level? Recommended: yes (the same call as the geometricalgebra task's open question 2).
