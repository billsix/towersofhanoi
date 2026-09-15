# Fully type, dataclass-ify, and Google-docstring all hanoi Python (src + tests)

**Status:** complete (2026-09-15) — `ty check src tests` is **0 diagnostics** (from 38),
`ruff check` clean, `ruff format --line-length=80` idempotent, 124 tests pass. Verified
**in-container** (`make shell-exec`), where `wx`/`pysnooper` resolve — the agent sandbox
lacks them, so a host `ty` run still shows phantom import errors. See "Outcome" below.
**Priority:** 4
**Difficulty:** 7

## Outcome (2026-09-15)

All three strands done across all 16 files (11 `src` + 5 tests):

1. **Types → `ty` clean.** The real baseline (in-container, wx resolved) was **38**
   diagnostics, not the 18 a host run shows. Cleared them all. The big group was
   `hanoigui.py`'s `self.session: Optional[GameSession]` — every handler ran after
   `_new_game` set it, so it was redeclared **non-Optional** (`self.session: GameSession`,
   assigned in `_new_game`), clearing ~20 at once. Others: Optional-narrowing in
   `board_renderers._paint_game`/`_redraw` (pass the narrowed `game`/`labelling` as params),
   `engine`/`hanoigui` `registry.get(name)` where `name` came from `names()` (`assert ... is
   not None`), `StepResult` pegs in the `result.ok` branch (assert), `commands.parse` relabel
   labels made a fixed `tuple[int,int,int]` (dropped a stale `# type: ignore`), `HELP_TEXT:
   str` (so `.splitlines()` is `list[str]` not `list[LiteralString]` — `list` is invariant),
   `wx.Size(...)` instead of a bare tuple, and a constructor contract `BoardRenderer.__init__(
   self, parent)` so `type[BoardRenderer]` is callable. **One latent bug fixed:**
   `ValidMove.action` used `default_factory=noop`, which set the default to `None` (the
   *result* of `noop()`) — now `default_factory=lambda: noop`.
2. **Dataclasses.** `RecipeRegistry` was the only convertible plain class → `@dataclass` with
   `_by_name: dict[str, Recipe] = field(default_factory=dict)`. Correct exclusions (left as
   plain classes): `GameSession` (`__init__` builds a `HanoiGame` from a param), the
   `BoardRenderer` ABC + two wx renderers, `HanoiFrame` (wx.Frame subclass), `Labelling`
   (Enum).
3. **Google docstrings** on every module, class, function, and method; dataclass field docs
   moved into `Attributes:` sections; existing rich prose preserved and reformatted.

**How it was built:** three subagents did the mechanical type/docstring/dataclass pass on the
leaf files (recipe+presenter; cli+curses+standalone; the 5 tests) in parallel; the four
`ty`-error-bearing source files (`board_renderers`, `commands`, `engine`, `hanoigui`) and the
central `ty`/ruff/pytest gate were done here. The gate ran in-container via `make shell-exec`.

**Maximal local annotations (done 2026-09-15, maintainer's explicit choice):** after the
signature pass, the maintainer chose to annotate **every** local binding and module constant
for uniformity — including the obvious `int`/`bool`/`str` ones the standard would let you skip
as "pure noise" — as a **project-specific** decision, *without* changing the shared
`~/.claude/reference/python-coding-standard.md` (its "annotate where it adds information"
default stands for other repos). ~260 bindings annotated across all 16 files (via five parallel
subagents, then the central `ty` gate). Loop/unpack and `with ... as` targets get a
declaration line *above* the statement (can't annotate inline). The two method-probing
`getattr(lb, "SetFirstItem"/"EnsureVisible", None)` results were annotated too, at the
maintainer's request, as `Callable[[int], object] | None`. **The only bindings left bare are
the genuinely un-annotatable / counterproductive ones:** comprehension & generator-expression
variables (separate scope — a hard language limit), and the `xrcctrl = wx.xrc.XRCCTRL` function
alias (annotating its return would narrow XRCCTRL's dynamic result and break the
specific-control method calls downstream). Re-verified
in-container: `ty` 0, `ruff` clean at 80, format idempotent, 124 tests pass.

**Config fix (done 2026-09-15, maintainer-approved):** `python/pyproject.toml` had no
`[tool.ruff] line-length`, so bare `ruff format` defaulted to **88** while
`entrypoint/format.sh` forced `--line-length=80` — the two disagreed. Fixed per the coding
standard ("set the limit in config, one place; remove per-invocation `--line-length` flags"):
added `line-length = 80` under `[tool.ruff]` and dropped the flag from `format.sh`. This also
made E501 (which `select` includes via `"E"`) lint at 80, which surfaced 10 over-80
docstring/comment lines the formatter can't rewrap — all reflowed to ≤80. Re-verified
in-container: `ruff check`/`ruff format --check`/`ty` all clean, 124 tests pass.

## BLUF

A comprehensive polish of **every** Python file in `python/` (source **and** tests), in three
strands (maintainer's ask, 2026-09-15):

1. **Types everywhere** — every function/method signature (params + return), and every local and
   global/module variable that isn't pure noise. Get `ty` fully clean.
2. **Dataclasses** — convert every class that *can* be a `@dataclass` into one.
3. **Google-style docstrings** — a docstring on every module, class, function, and method, in
   **Google style** so it *could* render in Sphinx (via `napoleon`) — even though we aren't setting
   that up now.

"Done" = `ty check src tests` is clean, `ruff` is clean, the suite still passes, every eligible
class is a dataclass, and every module/class/callable has a Google-style docstring.

(This supersedes the earlier narrower "type-annotate-all-src" task — same core, now covering tests,
dataclasses, and docstrings too.)

## Context — read first

- **Checker: `ty`** (Astral), already installed in the image (`entrypoint/01-install-base.sh`). Run
  from `python/`: `ty check src tests`. Baseline **17 diagnostics** in `src` (all pre-existing —
  e.g. `engine.py` `result.from_peg + 1` where `from_peg` is `Optional[int]`; add `Optional`/guards).
  `tests/` is currently unchecked — expect more once it's covered.
- **`ruff`** runs via `entrypoint/format.sh` / `make format` (check + format, line-length 80). Keep it
  green. If a companion `make type-check` exists by then (see `tasks/add-make-type-check.md`), use it.
- **The shared Python coding standard governs the *how*** — read
  `~/.claude/reference/python-coding-standard.md` (§ "Type annotations — annotate generously"):
  signatures always; locals as much as reasonable; loop/unpack targets typed on the line *above*
  (not comprehension vars); read-only container params take `Sequence`/`Mapping`, not `list`/`dict`;
  **don't fight the checker** — leave a value inferred (with a one-line why) rather than mangle logic.
- **Files** (`python/src/hanoigame/`): `board_renderers.py`, `commands.py`, `engine.py`,
  `hanoicli.py`, `hanoigame.py` (curses), `hanoigui.py` (wx), `hanoiiterative.py`, `hanoimodel.py`,
  `hanoirecursive.py`, `presenter.py`, `recipe.py`; plus everything under `python/tests/`.

### Strand 2 — dataclasses ("every class that can be")

- **Already dataclasses** (leave as-is, just ensure typed + docstringed): `Recipe`, `Recorder`,
  `StepResult` (`recipe.py`); the command classes (`commands.py`); `DispatchResult` (`engine.py`).
- **Candidates to audit/convert** — plain data/behaviour classes not yet dataclasses (e.g. in
  `hanoimodel.py`, `board_renderers.py`). Convert where a dataclass genuinely fits (fields + simple
  init); keep `frozen=True` where the type is logically immutable.
- **NOT candidates** (say so at the site if it's non-obvious): `wx.*` subclasses (`HanoiFrame`,
  dialogs — a framework base class with its own `__init__`), `Enum`s (`Labelling`), and any class
  whose `__init__` does real work a dataclass can't express. `@dataclass` "that can be" means exactly
  that — don't force it.

### Strand 3 — Google-style docstrings

- Every module (top-of-file), class, function, method gets a docstring. **Google style** — `Args:`,
  `Returns:`, `Raises:`, `Attributes:` (for classes/dataclasses) sections — the format Sphinx's
  `napoleon` extension renders. We are **not** wiring Sphinx for this code now; the point is that the
  docstrings would render cleanly if we ever did.
- Keep them accurate and terse; a one-line summary line + sections only where they add information.
  Preserve the good explanatory docstrings/comments already present (e.g. `recipe.py`'s module
  docstring, the rebinding helpers) — reformat to Google sections where useful, don't discard content.

## Plan

- [ ] **Types:** per file (src then tests), annotate every signature + local; clear the 17 `src`
      diagnostics + whatever `tests` surfaces; `ty check src tests` → 0.
- [ ] **Dataclasses:** audit each class; convert the eligible ones; note the exclusions in-code.
- [ ] **Docstrings:** add/convert to Google style on every module/class/callable, src + tests.
- [ ] **Verify:** `ty check src tests` clean, `ruff check` clean, `pytest tests/ -q` green, and
      spot-check that a couple of docstrings parse as valid Google style (napoleon-compatible).

## Notes

- Big, mechanical-with-judgment; do it file-by-file so a regression localises. The wx frontend
  (`hanoigui.py`) is the trickiest — framework-fixed method names are exempt from house naming
  (suppress narrowly, with a reason), and wx is largely untyped so annotate the *hanoi* side and
  don't chase `Any` from wx.

## Related

- `tasks/add-make-type-check.md` — the `make type-check` gate this task should end green against.
- `~/.claude/reference/python-coding-standard.md` § "Type annotations".
- `tasks/reference/architecture-overview.md` — the module map + the recipe/rebinding design.
