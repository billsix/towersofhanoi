# Type-annotate all of hanoi's src Python — every function, method, and local

**Status:** proposed — needs go-ahead
**Priority:** 4
**Difficulty:** 5

## BLUF

Add type annotations **everywhere** in `python/src/hanoigame/` — every function and method
signature (params + return) **and every local variable** — and get `ty` fully clean. Maintainer's
ask (2026-09-14): *"use types in hanoi src python code everywhere, every local variable, every
function, every method."* Baseline today: `cd python && ty check src` reports **19 diagnostics**
(all pre-existing; none in `recipe.py`/`engine.py`/`hanoigui.py`, which were just annotated for the
recipe-rebinding feature). "Done" = every def/method has a typed signature, locals are annotated
per the standard below, `ty check src` is clean, and the suite still passes.

## Context — read first

- **The checker is `ty`** (Astral). Run from `python/`: `ty check src` (add `tests` too if the gate
  should cover tests). `ruff` also runs (`entrypoint/format.sh`) and enforces some naming/idiom
  rules; check whether `format.sh` already invokes `ty` and, if not, whether to add it (propose,
  don't silently wire — see the shared standard's gate rules).
- **The shared Python coding standard governs how to annotate** — read
  `~/.claude/reference/python-coding-standard.md` (§ "Type annotations — annotate generously"):
  signatures always; locals as much as reasonable including in library code (`r: Rotor = a * b`);
  skip only where it would be pure noise (`n = 3`) and **when in doubt, annotate**; loop/unpack
  targets get a declared type on the line *above* (they can't be annotated inline), except a
  comprehension/genexpr var (separate scope, stays inferred); read-only container params take the
  covariant supertype (`Mapping`/`Sequence`), not invariant `dict`/`list`; **don't fight the
  checker** — a locally-correct annotation that forces edits to unrelated logic or breaks
  flow-narrowing isn't worth it, leave it inferred and say why.
- **Files to cover** (`python/src/hanoigame/`): `board_renderers.py`, `commands.py`, `engine.py`,
  `hanoicli.py`, `hanoigame.py` (curses), `hanoigui.py` (wx), `hanoiiterative.py`, `hanoimodel.py`,
  `hanoirecursive.py`, `presenter.py`, `recipe.py`. (`recipe.py`/`engine.py`/`hanoigui.py` are
  already signature-typed and ty-clean, but their **locals** may not all be annotated yet — sweep
  them too for the "every local" bar.)
- **wx caveat:** `hanoigui.py` overrides wx framework methods (`OnInit`, event handlers) whose names
  are externally fixed — annotate their signatures but keep the names; a `ty`/`ruff` complaint about
  a framework-fixed name is the tool being wrong (suppress narrowly with a reason at the site, per
  the standard's "externally-defined name wins").

## Plan

- [ ] Enumerate the 19 current `ty` diagnostics; fix each (they are the concrete starting worklist).
- [ ] Per file: annotate every def/method signature, then every local variable (per the standard —
      loop/unpack targets declared on the line above; genexpr vars left inferred).
- [ ] Prefer precise types (`Labelling`, `HanoiGame`, `Optional[int]`, `Sequence[int]`, the project's
      own dataclasses) over `Any`; add `Optional`/guards where a value can be `None` (the pattern that
      the rebinding fix already hit: `label_to_tower` returns `int | None`).
- [ ] Decide + propose whether `ty check src` (and `tests`) joins the `format.sh`/make gate.
- [ ] Verify: `ty check src` clean (0 diagnostics), `ruff check` clean, and
      `PYTHONPATH=src python3 -m pytest tests/ -q` still green (117 tests today).

## Notes

- This is the language-agnostic "enforce a rule with discretion" shape from the shared conventions:
  fix the safe bulk automatically, annotate precisely, and where a correct annotation would fight the
  checker or the wx framework boundary, opt out explicitly in-code with a written reason rather than
  mangle the logic.

## Related

- `~/.claude/reference/python-coding-standard.md` § "Type annotations — annotate generously".
- `tasks/record-recipe-bindings-and-show-rebinding.md` (archived after commit) — added the first
  fully-annotated helpers (`recipe.py` `rebinding`/`format_rebinding`) as a model.
