# Implementation Plan

Companion to `NOTES.md` (which has the *why*). This file is the *order of
work* — checkbox-driven so a future session can skim it, see where we left
off, and resume.

**Current step:** all five planned steps complete and signed off by Bill.
Remaining items are optional polish — see the "What's left" section at the bottom.

---

## Why this ordering

CLI is the simpler frontend, so building it second — *after* extracting a
UI-agnostic presenter — flushes out boundary mistakes before they multiply
across three frontends. Recipes are model-layer and independent of UI, so
they slot in before the curses rework, letting the new curses UX include
recipe controls natively rather than retrofitting. Curses redesign and
wxWidgets are pure UI consumers of a stable core.

Tradeoff: the curses Bill uses day-to-day stays as-is until step 4. Accepted.

---

## Step 1 — Extract a UI-agnostic presenter and command grammar

**Status:** complete (62 tests passing; awaiting Bill smoke-test of curses)

- [x] Add `hanoigame/presenter.py` with pure `render(game, labelling) ->
      list[str]`.
- [x] Move `Labelling`, `change_labels_on_pegs`, `peg_color` to presenter.
- [x] Move layout helpers off `HanoiGame` (`min_cols`, `min_rows`,
      `total_game_content_width` (renamed `total_width`), `peg_visual_width`,
      `peg_gap`, `disk_char_width`, `padding_left`, `max_disk_size`). They
      take `num_disks` as a parameter now.
- [x] Add `hanoigame/commands.py` with `MoveCmd`, `RelabelCmd`, `SaveCmd`,
      `ApplyCmd`, `ListCmd`, `HelpCmd`, `QuitCmd`, `EmptyCmd`, `ParseError`
      and `parse(line) -> Command`.
- [x] `test_presenter.py` (15 tests) and `test_commands.py` (45 tests).
- [x] Curses front-end retargeted to import from presenter. Curses still
      does its own coloured drawing — no visual regression. The new parser
      is built but not yet wired into curses input; that's step 4.

**What's where now:**
- `hanoimodel.py` — pure state (`HanoiGame`, `Move`, `ValidMove`,
  `move_options()`).
- `presenter.py` — `Labelling`, layout maths, colour table, `render()`,
  `render_with_legend()`, `labels_to_towers()`, `label_to_tower()`,
  `labelling_for()`.
- `commands.py` — typed `Command` ADT and `parse()`.
- `hanoigame.py` — curses front-end, unchanged behaviour.

**Resumption notes:** The point of this step is the boundary. If CLI in
step 2 feels awkward, the boundary is wrong — fix here before continuing.

---

## Step 2 — Build the CLI on top of the presenter

**Status:** complete (73 tests passing; awaiting Bill smoke-test)

- [x] `hanoigame/hanoicli.py` with `main()` and a programmatic `run(in, out)`
      so tests can drive it with `StringIO`.
- [x] Script entry: `hanoi-cli = "hanoigame.hanoicli:main"`.
- [x] Loop: render board, list valid moves under current labelling, prompt,
      parse, dispatch.
- [x] Illegal-move messages: "Peg N is empty" and "Can't put disc X on
      disc Y — larger on smaller", expressed in the user's current labels.
- [x] Win banner: `Solved! N moves (minimum M).` plus
      `Optimal solution!` or `K more than the minimum.`.
- [x] Recipe commands (`save`/`apply`/`list`) parse and report
      "(recipes land in step 3 — not implemented yet)".
- [x] `test_hanoicli.py` — 11 tests covering the optimal sequence, an
      extra-moves run, both illegal-move messages, recipe stubs, quit,
      EOF, relabel echo, help, parse errors, disc-count re-prompting.

**Resumption notes:** Boundary held up. The CLI is ~190 lines and most of
that is dispatch + prompting; the model and presenter did the work. Step 3
just needs to add a `move_history` field to `HanoiGame` and a Recipe
registry, then wire `save`/`apply`/`list` in this same dispatch.

---

## Step 3 — Recipes in the model

**Status:** complete (102 tests passing; awaiting Bill smoke-test)

- [x] `hanoigame/recipe.py` — `Recipe`, `Recorder`, `RecipeRegistry`,
      `StepResult`, `apply_iter` (lazy / step-mode), `apply` (eager wrapper).
- [x] **Label-space storage** — `Recorder.record(from_label, to_label)`
      stores what the user typed; `apply_iter` translates through the
      *current* labelling at replay time. `HanoiGame` was *not* modified;
      the recorder lives beside it (frontend-side) so the model stays pure.
- [x] No disk-count gating on `apply` — replay is allowed across sizes
      because that's the whole point (Bill's worked example: a 2-disc
      recipe applied to a 3-disc game). Move legality is the gatekeeper.
- [x] `apply` records each successful step into the active recorder, so a
      chained sequence (apply a sub-recipe, then play more, then save)
      captures the entire journey in the new recipe.
- [x] `test_recipe.py` — 11 tests including the marquee
      `test_apply_recipe_through_relabel_solves_subproblem`, which
      reproduces Bill's exact worked example: a 2-disc-from-1-to-3 recipe,
      applied on a fresh 3-disc game after `relabel 1 3 2`, lands the small
      two discs on physical peg 1 with the size-3 disc untouched.
- [x] CLI wiring: `save` during play errors with a hint about the post-win
      prompt; `apply <name>` replays through the current labelling and
      streams `step N: from -> to` lines; `list` shows
      `name (D discs, M moves)`; the post-win prompt accepts any non-empty
      string as a recipe name. Registry persists across games inside one
      `run()` invocation.

**Resumption notes:** Recipe persistence to disk is still on `TODO.org`
("scriptable moves: save to filename / replay filename"). The current
in-memory registry is exactly the right shape for that — add a load/save
pair on `RecipeRegistry` and a `--recipes-file` CLI flag whenever it's
wanted.

---

## Step 4 — Curses UX rework

**Pass 1 status:** complete (112 tests; awaiting Bill smoke-test)

- [x] New `engine.py` with `GameSession` + `dispatch(cmd) -> DispatchResult`.
      Pulls `_try_move`, `_do_apply`, `_do_show`, `_do_list`, relabel
      handling, and the mid-game `save` rejection out of the CLI into a
      shared module both frontends use.
- [x] `hanoicli.py` refactored to a thin wrapper over `GameSession`. All
      24 existing CLI tests pass with no behaviour change.
- [x] `hanoigame.py` rewritten from scratch:
      - Drops the overlay menu and the arrow-key picker entirely.
      - Layout: status row at top, board centred, message area, hint line,
        prompt at the bottom.
      - Typed input via a `getch()` loop with backspace + Enter.
      - Same command grammar as CLI (`1 -> 3`, `relabel 1 3 2`, `apply`,
        `show`, `list`, `help`, `quit`).
      - Coloured rendering preserved; the dual-label-row treatment from
        the recent change carries through.
      - Post-win save prompt; play-again prompt.
      - Opportunistic cleanup landed: the `stdstr=` typo is gone (the
        whole code path is replaced); the six `elif key == ord('N'):`
        relabel branches are gone (relabel goes through the typed
        command); the on-screen hint reflects the new model.

**Pass 2 plan (not yet started):**

- [ ] Top-right recipe-list panel that updates as recipes are saved.
- [ ] F-key shortcuts for common commands (F1 = help, F4 = recipe list,
      F10 = quit) on top of the typed grammar — convenience, not a
      replacement.
- [ ] Step-mode toggle for `apply` so the user can pause between steps and
      watch the recipe execute one move at a time. Engine already exposes
      `apply_iter`; just need a UI loop around it.
- [ ] Window-resize handling (currently just ignores `KEY_RESIZE`).

**Resumption notes:** The shared dispatcher (`engine.GameSession`) is the
load-bearing piece. Step 5 (wxWidgets) plugs into the same `dispatch(cmd)`
entry point — buttons emit `Command` values, dispatcher applies them.

---

## Step 5 — wxWidgets frontend

**Status:** complete and signed off by Bill. 112 tests still pass.

- [x] `hanoigame/hanoigui.py` — `wx.Frame`-based GUI, all input via
      buttons, no typed input except the recipe-name dialog.
- [x] Layout (top to bottom): disc spinner + New Game + status row;
      monospace board panel; six Move buttons (auto-enabled per
      `game.move_options()`, disabled after a win); six Relabel
      permutation buttons (active labelling's button is disabled to
      visually mark the current state); Recipe `wx.ListBox` showing
      `name (D discs, M moves)` plus Save Current / Apply Selected /
      Show Selected; Last-action multi-line read-only `wx.TextCtrl`.
- [x] Behaviour goes through `engine.GameSession.dispatch` exactly the
      same as CLI and curses — buttons emit `MoveCmd`, `RelabelCmd`,
      `ApplyCmd`, `ShowCmd` values, the dispatcher applies them, the
      returned `lines` populate the message panel.
- [x] Save Current pops a `wx.TextEntryDialog` (default name
      `solve-<n>`), only valid after winning (otherwise pops an info
      dialog explaining when it works). Show Selected pops the recipe's
      step list in a `wx.MessageBox`.
- [x] Post-win lockout: move + relabel + apply buttons disabled until
      New Game is clicked. Save Current and Show Selected stay enabled.
- [x] `hanoi-gui = "hanoigame.hanoigui:main"` in `pyproject.toml`.
- [x] `Dockerfile` installs `python3-wxpython4` from Fedora 44 dnf.
- [x] README documents the three front-ends and the X-forwarding flags
      needed to run the GUI from inside the container.

**Resumption notes:** No automated tests — wx requires a display.
Module imports `wx` at top level; that's fine because nothing else
imports `hanoigui` (CLI tests don't need it). The shared `GameSession`
is what's load-bearing here, not the GUI plumbing — visual bugs are
easy to spot but the dispatch contract is already covered by the CLI
test suite.

---

## Cross-cutting items (do whenever they fit)

- [ ] Fix `[tools.ruff]` typo in `pyproject.toml` (should be `[tool.ruff]`).
- [ ] Tick off `TODO.org` UI helper unit tests once they move to the
      presenter (step 1 makes them testable).

---

## What's left

All five planned steps are complete. Optional follow-on work, in
roughly descending order of value:

1. **Recipe persistence to disk.** `TODO.org`'s "scriptable moves: save
   to filename / replay filename". The in-memory `RecipeRegistry` is the
   right shape — add `load(path)` / `save(path)` and a `--recipes-file`
   flag on `hanoi-cli` (or a Save/Load button in the GUI).
2. **Step-mode recipe replay.** `engine.apply_iter` already supports it
   (yields one move at a time). Add a UI surface — for the GUI, a
   "Step" button that calls `next()` on a stored iterator; for curses,
   a typed `step` / `next` command.
3. **Step 4 pass 2** — top-right recipe-list panel inside the curses
   layout, F-key shortcuts on top of the typed grammar (F1 help, F4
   recipe list, F10 quit), proper `KEY_RESIZE` handling.
4. **Cross-cutting cleanup** — the two items above (`[tools.ruff]`
   typo, `TODO.org` ticking).
5. **Recipe delete** in the GUI ListBox + a `delete <name>` command in
   the shared grammar. Currently the only way to remove a saved recipe
   is to overwrite it.
