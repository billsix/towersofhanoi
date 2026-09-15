# Fully type, dataclass-ify, and Google-docstring all hanoi Python (src + tests)

**Status:** complete (2026-09-15). `ty check src tests` = **0 diagnostics** (from a real
baseline of 38), `ruff` clean at 80, `ruff format` idempotent, 124 tests pass — all verified
**in-container** via `make shell-exec`/`make type-check`, where `wx`/`pysnooper` resolve (the
agent sandbox lacks them, so a host `ty` run shows phantom import errors and only 18 of the 38).
**Priority:** 4
**Difficulty:** 7

## What this was

A comprehensive polish of **every** Python file under `python/` (11 `src` + 5 tests), in three
strands the maintainer asked for: (1) types on every signature and every local; (2) convert
every class that *can* be a `@dataclass`; (3) a Google-style (napoleon-renderable) docstring on
every module, class, function, and method. It superseded the narrower `type-annotate-all-src`.
Two extensions landed on top: **maximal** local annotation (every binding, not just the
informative ones), and a **line-length config fix**. The durable "why" — the typing patterns,
the maximal-annotation convention, the gate, the line-width source-of-truth — was harvested into
`tasks/reference/architecture-overview.md` ("Typing, docstrings & the type-check gate"); this
doc is the work record.

## What was done

**Strand 1 — types → `ty` clean.** The real baseline (in-container, `wx` resolved) was **38**
diagnostics. The largest group was `hanoigui.py`'s `self.session: Optional[GameSession]`: every
handler runs after `_new_game` sets it, so it was redeclared **non-Optional**
(`self.session: GameSession`, assigned in `_new_game`), clearing ~20 at once. The rest:
Optional-narrowing in `board_renderers._paint_game`/`_redraw` (pass the narrowed
`game`/`labelling` in as params); `engine`/`hanoigui` `registry.get(name)` where `name` came
from `names()` (`assert … is not None`); `StepResult` pegs in the `result.ok` branch (assert);
`commands.parse` relabel labels rebuilt as a fixed `tuple[int, int, int]` (dropping a stale
`# type: ignore`); `HELP_TEXT: str` so `.splitlines()` is `list[str]` not the invariant
`list[LiteralString]`; `wx.Size(...)` instead of a bare tuple; and a constructor contract
`BoardRenderer.__init__(self, parent)` so `type[BoardRenderer]` is constructible. **A latent bug
fell out:** `ValidMove.action`'s `default_factory=noop` had set the default to `None` (the
*result* of calling `noop`); it is now `default_factory=lambda: noop`.

**Strand 2 — dataclasses.** `RecipeRegistry` was the one convertible plain class → `@dataclass`
with `_by_name: dict[str, Recipe] = field(default_factory=dict)`. The correct exclusions stayed
plain: `GameSession` (its `__init__` builds a `HanoiGame` from a param), the `BoardRenderer` ABC
and its two wx renderers, `HanoiFrame` (a `wx.Frame` subclass), and `Labelling` (an `Enum`).

**Strand 3 — Google docstrings** on every module, class, function, and method; dataclass field
docs moved into `Attributes:` sections; existing rich prose preserved and reformatted.

**Maximal local annotations** (a deliberate hanoi-specific choice, kept out of the shared
standard): after the signature pass, the maintainer chose to annotate *every* binding — locals,
module constants, loop/unpack/`with`-as targets — including obvious `int`/`bool`/`str` ones. ~260
bindings. Loop/unpack/`with` targets get a declaration line *above* the statement. The only
bindings left bare are the ones that can't be: comprehension/generator-expression variables
(separate scope), and the `xrcctrl = wx.xrc.XRCCTRL` alias (annotating its return would narrow
XRCCTRL's dynamic result and break downstream control-method calls). The two method-probing
`getattr(lb, "SetFirstItem"/"EnsureVisible", None)` results were annotated
`Callable[[int], object] | None`.

**Config fix.** `python/pyproject.toml` had no `[tool.ruff] line-length`, so bare `ruff format`
defaulted to 88 while `entrypoint/format.sh` forced `--line-length=80` — they disagreed. Added
`line-length = 80` under `[tool.ruff]` and dropped the flag from `format.sh`. That made E501 lint
at 80 too, surfacing 10 over-80 docstring/comment lines (which the formatter can't rewrap); all
reflowed to ≤80.

**How it was built.** The mechanical passes were fanned out to subagents (leaf files for the
strand pass; five for the maximal-annotation pass), with the `ty`-error-bearing source files and
the central `ty`/ruff/pytest gate done directly. `ty` was the safety net for the subagent work:
every guessed annotation was validated by the central in-container gate, so no wrong type
survived.

## Verification

In-container (`make type-check`, `make shell-exec`): `ty check src tests` → 0; `ruff check` clean
(E501 at 80); `ruff format --check` idempotent; `pytest` → 124 passed. `ty`'s signature coverage
was independently confirmed with ruff's `ANN` (flake8-annotations) rules — 0 missing
parameter/return annotations.

## Related

- `tasks/reference/architecture-overview.md` — "Typing, docstrings & the type-check gate" (the
  harvested rationale + patterns) and the module map.
- `tasks/archive/2026/09/15/add-make-type-check.md` — the `make type-check` gate this ends green
  against, implemented alongside.
- `~/.claude/reference/python-coding-standard.md` § "Type annotations" — the shared default this
  repo's maximal choice deliberately exceeds (and did not change).
