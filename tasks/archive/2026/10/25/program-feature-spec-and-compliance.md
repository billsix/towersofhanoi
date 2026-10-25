# A UI-independent feature spec for hanoi + verify every implementation against it

**Status:** COMPLETE (2026-10-25) — spec written (`tasks/reference/feature-spec.md`), Python reconciled
to it (the authority; no cruft found, nothing added beyond Python), and the Rust/C++/bash audit documented
below (§ Audit results). Gap-fixing is spun into per-language parity tasks (C++:
`tasks/archive/2026/10/25/cpp-add-wx-frontend-and-recipe-view-parity.md`; Rust: `tasks/rust-feature-parity-tauri-tui-gaps.md`).
Ready to archive after the work commit.
**Priority:** 4 **Difficulty:** 6
**Created:** 2026-10-25 (William Emerison Six <billsix@gmail.com>). Requested: "let's make a reference
document that defines what this program should allow, as far as features. these should be independent of
the UI, and should explain the rules of hanoi, and what the UI can show a user, and what it can allow the
user to do and why. the existing python code should be used to define it for now. Then, if there's TUI
specific advice, or GUI specific advice (menubars, button layout, etc.) that should be mentioned as well.
We should extract this all from the python source, and then verify that the python source implements all
of this and nothing more, and then for the other code in this project as well. For any new UI or language
that's made for it, we should verify compliance as we make it, or use the spec as a template."

## BLUF

Write a **UI-independent feature specification** for hanoi as a reference doc
(`tasks/reference/<name>.md`), extracted from the **Python package as the authority "for now"**. It
defines the rules of Hanoi, the domain concepts, and every **feature** — for each, *what the user can do,
what the UI must show, and why* (the teaching rationale) — followed by **UI-category addenda** (TUI/CLI
and GUI: menubars, button layout, etc.). Then verify **both directions**: the Python source implements
**all** of the spec and **nothing more**, and then audit each other implementation (Rust, C++, bash) for
compliance (producing a per-implementation gap list). The spec becomes the **parity authority**: every
current and future UI/language is checked against it, or uses it as the build template. "Done" = the spec
reference doc exists, Python is reconciled to it exactly, and each existing implementation has a recorded
compliance result (gaps feeding the relevant parity tasks).

## Context (read first)

- **The authority (for now): the Python package** `python/src/hanoigame/`. Extract the spec from:
  - `hanoimodel.py` — pegs, disks, legal-move rule, win condition (the rules).
  - `presenter.py` — the six peg **labellings**, default-label space, board rendering, the label rows.
  - `recipe.py` — `Recorder`/`Recipe`/`RecipeRegistry`, and **`rebinding`** (recipe labels → physical
    pegs), **`rebound_moves`**, **`format_rebinding_table`** (the text form of the GUI three-panel view).
  - `commands.py` + `engine.py` — the command grammar + dispatch (what actions exist, what each does,
    what is rejected and the reason).
  - Front-ends as UI-category evidence (NOT authority for the core): `hanoicli.py` (plain stdin/stdout +
    readline completion), `hanoigame.py` (ncurses TUI), `hanoigui.py` (wxPython GUI — menubar, board,
    three-panel recipe view). `board_renderers.py` for text vs 2D board.
- **Why Python is the authority:** the project convention is that the Python package is the **behaviour
  oracle**; all ports mirror it and must not drift (`CLAUDE.md`). This spec makes that authority explicit
  and UI-independent so ports conform to a *written* definition, not to each other.
- **Relationship to the parity tasks:** `tasks/archive/2026/10/25/cpp-add-wx-frontend-and-recipe-view-parity.md` (C++) and
  `tasks/rust-gui-use-shared-xrc.md` (Rust) become **spec-driven** — their "parity" is conformance to
  this spec. The maintainer decided (2026-10-25) full parity is the standard for *every* implementation.
- **Reference-doc nature:** this is durable knowledge ("what is TRUE"), so it lives in
  `tasks/reference/` and is never archived — updated in place as the program evolves (the spec leads, the
  code follows). See `tasks/reference/reference-doc-conventions` equivalents in the shared layer.
- **Existing related reference docs to fold in / point at, not duplicate:**
  `tasks/reference/architecture-overview.md` (dispatch data-flow + the default-label-space recipe
  invariant + per-file teaching intent) and the archived
  `tasks/archive/2026/09/14/record-recipe-bindings-and-show-rebinding.md` (why the rebinding is shown).

## Proposed structure of the spec reference doc (review before extraction)

Working name: `tasks/reference/feature-spec.md` (open question 1). Proposed sections:

1. **Purpose & teaching intent** — the program teaches solving by hand via peg **relabelling**
   ("solve small, relabel, replay"); every feature serves that. (From `CLAUDE.md` + the book intent.)
2. **The rules of Towers of Hanoi** — pegs, disks, the legal-move rule (a disk onto empty or a larger
   disk only), the win condition. UI-independent.
3. **Domain concepts (UI-independent)** — physical pegs vs the six **labellings**; **default-label
   space**; **recipes** (recorded in default-label space); **rebinding** (a recipe's labels → physical
   pegs under the current labelling); **rebound moves** (the recipe's moves expressed on the physical
   pegs). The vocabulary every UI shares.
4. **Features — what the user can do (UI-independent)** — one entry each: new game / set disk count; make
   a move (and what is rejected + the reason); relabel the pegs; record a recipe; save/name a recipe;
   reset recording; **view/invoke a recipe** → show the recipe + rebinding + rebound moves on the global
   (physical) pegs; win detection. Each entry states: *what it does*, *what the UI must let the user
   **see***, *what it must let the user **do***, and ***why*** (teaching rationale). This section fixes
   the C++ Part-B "invoke semantics" question for all UIs.
5. **What a UI must SHOW** — the board + current labelling; legal moves in the current labels; the recipe
   list; the three-panel recipe view (recipe moves | rebinding label→peg | rebound physical moves); win
   state; rejection reasons.
6. **UI-category guidance (advice, not core):**
   - **TUI / CLI** — the command grammar + tab-completion; the text board; the text three-panel
     (`format_rebinding_table`); screen-reader-friendly plain output.
   - **GUI** — menubar grouping (Game / Relabel / Recipe); button layout (e.g. moves always shown,
     illegal ones disabled, not hidden — so controls don't jump); the three-panel view as panels/columns;
     2D vs text board.
7. **Compliance checklist** — a per-implementation checklist (one row per feature/show-item) to audit a
   UI/language against the spec; the artifact used in the verification steps and for any new UI.

## Plan

1. **Extract** the spec from the Python source into the reference doc, in the structure above
   (UI-independent core first, then the TUI/GUI addenda). Cite the Python source for each item.
2. **Verify Python conforms exactly** — walk the spec against the Python front-ends/engine: every spec
   item is implemented (completeness), and Python does **nothing more** than the spec (if it does, either
   add it to the spec or flag it as cruft — open question 4). Reconcile until spec ⇔ Python.
3. **Audit the other implementations** — check `rust/`, `cpp/`, and `bash/` against the compliance
   checklist; record each one's result (conforms / gaps). Gaps feed the parity tasks (e.g. C++ Part B).
   bash is a partial/educational implementation — note which checklist rows apply to it.
4. **Make it the ongoing authority** — reference the spec from `CLAUDE.md` and the parity tasks; verify
   any new UI/language against the checklist as it's built, or use the spec as the build template.

## Audit results (2026-10-25)

Three parallel read-only audits of the other implementations against the §7 checklist (14 rows). Python
is the authority (✓ by construction). Verdicts: ✓ present / **p** partial / ✗ absent / **n/a** justified.

| # | Feature (short) | Rust | C++ | bash |
|---|---|---|---|---|
| 1 | pegs/disks/start | ✓ | ✓ | p (implicit in the move text) |
| 2 | legal-move rule | ✓ | ✓ | ✗ (no board/disk model) |
| 3 | win + count + optimal 2^N−1 | ✓ | p (no optimal shown) | ✗ |
| 4 | move + distinct rejection reasons | ✓ | p (illegal = disabled; no reasons) | n/a |
| 5 | six labellings / relabel never moves disks | ✓ | ✓ | ✓ (the `tr` filters — standout) |
| 6 | label row + physical ref when relabelled | ✓ | p (no physical 1,2,3 ref row) | n/a |
| 7 | colour follows label | ✓ (CLI n/a) | ✓ | n/a |
| 8 | valid-moves in current labels | p (**TUI missing**) | ✓ | n/a |
| 9 | record default-space + save post-win + overwrite | ✓ | p (not win-gated; no overwrite report) | p (representation only) |
| 10 | list recipes (name/discs/moves) | ✓ | p (names only) | n/a |
| 11 | show a recipe's moves | ✓ | ✗ | p (stdout *is* the moves) |
| 12 | apply under labelling (apply+record+stop-reason) | ✓ | p (**doesn't record** applied moves) | p (pipe composition) |
| 13 | **three-panel rebinding view on apply** | ✓ CLI/TUI/wx, **p Tauri** | ✗ | ✗ |
| 14 | help / quit / empty-input | ✓ CLI/TUI, p wx/Tauri | p (no help, no in-app quit) | n/a |

**Rust** — the shared `hanoigame` crate implements the **full spec** (all recipe/rebinding/three-panel
logic, unit-tested); gaps are presentation-only in two front-ends: **Tauri row 13** (`apply_recipe`
returns a one-line message + a standing label→peg line — missing the recipe-moves and rebound-physical
columns; the backend has `format_rebinding_table`/`rebound_moves` already) and **row 12** richness
(per-step log dropped); **TUI row 8** (no valid-moves line — CLI/wx/Tauri have it); **wx/Tauri row 14**
(wx Help is an About blurb; Tauri has no help). → `tasks/rust-feature-parity-tauri-tui-gaps.md`.

**C++** — the engine headers have the rules + `rebinding()`, but the ImGui GUI drives them directly with
no commands/engine-dispatch layer, so several Python behaviours are absent from *both* engine and GUI.
Biggest: **row 13** (no three-panel view — only a one-line status + a static middle-only label→peg
panel; engine lacks `rebound_moves`/`format_rebinding_table`), **row 11** (no view-recipe), **row 12**
(apply doesn't record applied moves). Plus partials: row 10 (names only), row 4 (no rejection reasons),
row 9 (save not win-gated, no overwrite report), row 3 (no optimal), row 6 (no physical ref row), row 14
(no help/in-app quit). → folded into `tasks/archive/2026/10/25/cpp-add-wx-frontend-and-recipe-view-parity.md` Part B.

**bash** — a **by-design non-interactive demo** of the relabelling method (solve scripts composed through
six `tr` relabel filters); it has no board/state, so rows 4,6,7,8,10,14 are legitimately **n/a**, not
conformance gaps. It cleanly embodies row 5 (relabel = a permutation on the move stream, never touches
disks) and demonstrates apply/recipe-representation as stream composition (rows 9/11/12 partial). The
✗ rows (2,3,13) reflect that it is not a game UI; **no parity task is warranted** — bash stays a demo.

## Open questions (resolved 2026-10-25 — all five taken per the maintainer's "your recommendation")

1. **Doc name** — `tasks/reference/feature-spec.md`? (or `program-behavior-spec.md` / `what-hanoi-does.md`).
2. **Single doc vs a layered set** — one sectioned reference doc (recommended to start), or a
   `tasks/reference/<set>/` with an L0 capsule + per-area docs if it grows large?
3. **Depth of the UI-category advice** — a short "principles + the key layout decisions" (recommended),
   or an exhaustive widget-by-widget prescription?
4. **"implements … nothing more"** — when Python does something not in the spec, default to **adding it to
   the spec** (Python is authority), or flag it as candidate cruft for your review? (Recommend: add to the
   spec, but list each such addition so you can veto.)
5. **Audit depth this round** — produce the spec + the Python exact-reconcile now, and the rust/cpp/bash
   audit as a documented pass (recommended), or also fix the gaps in the same effort (larger — likely
   separate per-language tasks)?

## Related

- Authority: `python/src/hanoigame/` (see Context for the per-file map).
- Spec-driven parity tasks: `tasks/archive/2026/10/25/cpp-add-wx-frontend-and-recipe-view-parity.md`,
  `tasks/rust-gui-use-shared-xrc.md`.
- `tasks/reference/architecture-overview.md` (dispatch data-flow + recipe invariant) and
  `tasks/archive/2026/09/14/record-recipe-bindings-and-show-rebinding.md` (rebinding teaching rationale).
