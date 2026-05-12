# Implementation Plan

Companion to `NOTES.md` (which has the *why*). This file is the *order of
work* — checkbox-driven so a future session can skim it, see where we left
off, and resume.

**Current step:** steps 6 (XRC extraction) and 7 (UI redesign — menu
bar, status bar, big moves counter, deleted redundant chrome) both
implemented; awaiting Bill smoke-test. 112 tests still pass. Steps 8
and 9 (graphics + OpenGL board renderers) are planned but not started.
Optional follow-on polish lives in the "What's left" section at the
bottom.

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

## Step 6 — Extract wxWidgets UI to XRC

**Status:** implemented (112 tests still pass; awaiting Bill smoke-test).

**Goal:** Move the imperative `HanoiFrame._build_ui()` (currently ~140 lines
of `wx.BoxSizer` / `StaticBoxSizer` / `wx.Button(...)` wiring in
`hanoigui.py`) into a declarative `.xrc` resource. Python keeps event
handling, dynamic enable/disable, font choice, and the rendering loop; the
widget tree itself becomes data.

**Why this is worth doing now:** the layout has been stable through step 5
sign-off — five releases of UX iteration have settled it — so the cost of
churning XML is low. The teaching value is the chief motivation: Bill
teaches wxPython, and an XRC-backed example is more pedagogically useful
than a hand-built one. Optimise for readability of the XML, not minimal
line count.

### Tasks

- [x] Add `python/src/hanoigame/hanoi.xrc` containing one
      `<object class="wxPanel" name="HanoiPanel">` with the full widget
      tree. Named children (so Python can fetch each via
      `wx.xrc.XRCCTRL`):
      - Top row: `disc_dec` (`−` button), `disc_label` (count
        `wxStaticText`), `disc_inc` (`+` button), `new_game` button,
        `status_label` (`wxStaticText`).
      - `wxStaticBoxSizer` "Board" wrapping `wxTextCtrl` named `board`
        (multi-line, read-only, HSCROLL).
      - `wxStaticBoxSizer` "Move" with six `wxButton`s named
        `move_1_2`, `move_1_3`, `move_2_1`, `move_2_3`, `move_3_1`,
        `move_3_2`, labels `"1  →  2"` etc.
      - `wxStaticBoxSizer` "Relabel pegs (physical 1, 2, 3 →)" with
        six buttons named `relabel_1_2_3`, `relabel_1_3_2`,
        `relabel_2_1_3`, `relabel_2_3_1`, `relabel_3_1_2`,
        `relabel_3_2_1`.
      - `wxStaticBoxSizer` "Recipes" with `wxListBox` named
        `recipe_list` and three buttons `recipe_save`,
        `recipe_apply`, `recipe_show`.
      - `wxStaticBoxSizer` "Last action" wrapping `wxTextCtrl` named
        `message`.
      - Preserve current proportions/borders so the board absorbs
        vertical slack (it's the only `proportion=1` child of the
        outer vertical sizer today; keep that).

- [x] Rewrite `_build_ui()` in `hanoigui.py`:
      1. `import wx.xrc`; load the file via
         `importlib.resources.files("hanoigame").joinpath("hanoi.xrc")`
         and `wx.xrc.XmlResource.Get().Load(str(path))`.
      2. `self.panel = wx.xrc.XmlResource.Get().LoadPanel(self,
         "HanoiPanel")`, wrap in a sizer that fills the frame.
      3. Stash every named control on `self` via `wx.xrc.XRCCTRL(self,
         "<name>")` — `self.board`, `self.message`,
         `self.status_label`, `self.disc_count_label`,
         `self.recipe_list`, `self.save_btn`, `self.apply_btn`,
         `self.show_btn`.
      4. Populate `self.move_buttons` and `self.relabel_buttons` by
         iterating `ALL_LABEL_PAIRS` / `ALL_RELABEL_PERMUTATIONS` and
         looking up `XRCCTRL(self, f"move_{f}_{t}")` etc.
      5. Apply the monospace `wx.Font` to `board`, `message`,
         `disc_count_label`, `status_label`, `recipe_list` (system
         font discovery doesn't belong in XRC — keep it in Python).
      6. Wire events with
         `self.Bind(wx.EVT_BUTTON, handler, id=wx.xrc.XRCID("name"))`.
         Lambdas still close over the `(from, to)` pair for the
         twelve dynamic buttons, same as today. Direct binds for
         `disc_dec`, `disc_inc`, `new_game`, `recipe_save`,
         `recipe_apply`, `recipe_show`. Keep
         `self.board.Bind(wx.EVT_SIZE, self._on_board_resize)`.

- [x] `pyproject.toml`: added `[tool.setuptools.package-data]` with
      `hanoigame = ["hanoi.xrc"]` so the file ships in the wheel.

- [ ] Smoke-test (Bill, container with X-forwarding): launch
      `hanoi-gui`, play a 3-disc game to win, save as a recipe,
      relabel, apply the recipe, confirm post-win lockout still
      disables Move/Relabel/Apply but leaves Save/Show/New Game
      live. Confirm the board stays bottom-centred on resize.

### Out of scope

- **No behaviour changes.** Pixel-identical layout, same handlers,
  same dispatch path through `engine.GameSession`.
- **No XRC `<handler>` usage.** Lambdas capturing from/to pairs are
  clearer in Python than in XML attributes. Bindings stay in
  `_build_ui()`.
- **No tests.** The existing 112 tests don't import `hanoigui` (it
  pulls in `wx`); that stays true. XRC parse errors will surface at
  launch time, which is acceptable for a frontend module.

### Resumption notes

The two load-bearing risks are (1) `LoadPanel` returning `None`
because a name in the XRC doesn't match what Python looks up — keep
the XRC names and the Python `XRCCTRL` calls in lockstep, and (2)
the file not shipping in the wheel — verify with an out-of-tree pip
install before declaring done. If `XRCCTRL` returns `None` for a
control, that's the symptom of either bug.

After this lands, step-mode recipe replay (item 2 in "What's left")
becomes the natural next pick — the XRC will gain one `Step` button
alongside `Apply`, which is a small, isolated change in both files.

---

## Step 7 — wxWidgets UI redesign

**Status:** implemented (112 tests still pass; awaiting Bill smoke-test).

**Goal:** make the board the hero and stop showing redundant chrome.
The pre-redesign UI duplicated information across multiple places —
disc count appeared in the top toolbar *and* on the board; labelling
appeared in the status string *and* on the disabled relabel button;
recipe count appeared in the status string *and* as the list length.
The "Last action" multi-line panel was 110px tall for what was almost
always a one-line message. Disc count + New Game lived as permanent
top-row controls even though the user touched them twice per game.

### What changed

- [x] **Menu bar** (Python, on the frame, not in XRC):
      - `Game → New Game…` (Ctrl+N) → `wx.NumberEntryDialog` for disc
        count.
      - `Game → New Game (Same Size)` (Ctrl+Shift+N) → reuses last
        disc count.
      - `Game → Quit` (Ctrl+Q).
      - `Help → About`.
- [x] **`wx.StatusBar`** at the bottom of the frame replaces the
      former "Last action" panel. Single-line action feedback ("Moved
      1 → 3.", "Labels: 1 3 2", "Applied 'solve-2' — 3 moves."). Multi-
      line content that mattered (illegal-move explanations, recipe
      contents, win banner) goes to dedicated `wx.MessageBox` /
      `wx.MessageDialog` popups instead of being buried in a panel.
- [x] **Big moves counter** at the top of the panel —
      `Moves: 0` in 22pt bold teletype. The one number the user can't
      read off the board, made unmistakable. After a win it morphs to
      `Solved in N` until the next New Game.
- [x] **Win flow** is now a modal `wx.MessageDialog` with custom
      Yes/No labels ("Save as recipe…" / "Not now") — no more burying
      the win text in the message panel. Yes wires into the same
      `_save_recipe_with_prompt()` the Save Current button uses, so
      the recipe-save logic stays in one place.
- [x] **Reordered** Relabel above Move in the XRC. Relabel is the
      pedagogical lever (per NOTES.md it's "the load-bearing part");
      Move is just execution.
- [x] **Deleted entirely**: the top toolbar (disc −/+ buttons, count
      label, New Game button, status label) and the "Last action"
      `wxStaticBoxSizer` with its 110px TextCtrl. `disc_count_label`,
      `status_label`, `message`, `_adjust_disc_count`, and
      `_set_message` are all gone from `hanoigui.py`.
- [x] Window height dropped from 900 to 820 since the deletions
      bought back vertical space.

### What's still in XRC

19 named controls (was 24): `HanoiPanel`, `moves_label`, `board`,
six `move_*`, six `relabel_*`, `recipe_list`, `recipe_save`,
`recipe_apply`, `recipe_show`.

### Out of scope

- **No graphical board.** Clickable pegs would be the natural next
  step, but plain-text rendering is the explicit cross-frontend
  parity decision in NOTES.md. Move buttons stay.
- **No multi-field status bar.** Single field, latest action. If a
  permanent "Won!" indicator turns out to be wanted, that's a second
  status bar field — easy add later.

### Resumption notes

The wx.adv module isn't used (and wasn't worth the dependency for an
About box) — `wx.MessageBox` covers it. If a richer About dialog is
wanted later, `wx.adv.AboutDialogInfo` + `wx.adv.AboutBox` is the
upgrade path.

---

## Step 8 — Graphics board renderer (2D)

**Status:** not started.

**Goal:** A genuinely good-looking GUI board view without breaking
CLI / curses parity. ASCII stays the cross-frontend default; the GUI
gets a `View → Board Style → Text / Graphics` toggle that swaps in
a procedurally-drawn `wx.Panel`.

**Why this over SVG:** Towers are procedurally-defined shapes — a
10-tall stack with per-size colors is two for-loops, not 10 SVG
assets. `wx.GraphicsContext` already gives antialiased rounded
rectangles, gradients, and shadows. No new dependencies.

### Architecture — explicit renderer abstraction

Avoids `if mode == "graphics"` branches inside `_update_board`.

```python
class BoardRenderer:                  # ABC
    def widget(self) -> wx.Window: ...
    def update(self, game, labelling) -> None: ...

class TextBoardRenderer:       # wraps today's wx.TextCtrl path
class GraphicsBoardRenderer:   # wx.Panel + EVT_PAINT + wx.GraphicsContext
```

`HanoiFrame` holds one `self.board_renderer`. Swapping destroys the
current widget and inserts the new one into the Board sizer slot.
`HanoiGame` and `presenter`'s color palette are untouched.

### Tasks

- [ ] New `hanoigame/board_renderers.py`: `BoardRenderer` ABC,
      `TextBoardRenderer` (lifted from current `_update_board` +
      the `wx.TextCtrl` it owns), `GraphicsBoardRenderer`.
- [ ] `GraphicsBoardRenderer`:
      - `wx.Panel` subclass with `EVT_PAINT` and `EVT_SIZE`.
      - Three vertical rounded-rect pegs centered horizontally,
        stretching to fill panel height.
      - Each disc as a horizontally-graded rounded rectangle, width
        proportional to size, color from `presenter.peg_color` (or
        a parallel palette so curses ↔ graphics colors track).
      - Subtle drop shadow per disc; if `wx.GraphicsContext.SetShadow`
        is unavailable on Fedora's wx build, fall back to a darker
        rounded-rect drawn 2px offset below.
      - No animation; `update()` invalidates the full panel.
      - No click-to-move; existing Move buttons remain the input.
- [ ] `View` menu in hanoigui.py menu bar with radio items
      `Text` / `Graphics`. Selection calls `_swap_renderer(cls)`.
- [ ] `_swap_renderer`: detach the current renderer's widget from
      the Board sizer, destroy it, instantiate the new renderer,
      attach its widget, `Layout()`.
- [ ] XRC: replace the named `board` `wxTextCtrl` with a placeholder
      `wxPanel` named `board_slot`. The text path moves inside
      `TextBoardRenderer`'s constructor.
- [ ] Smoke-test (Bill, X-forwarding): toggle Text ↔ Graphics mid-
      game; verify state matches in both; verify resize.

### Out of scope

- **Animation** (disc tween between pegs). Easy to bolt on later.
- **Click-to-move** (hit-testing). Move buttons stay.
- **Per-disc artwork** beyond solid color + gradient.
- **CLI / curses changes** — those keep the presenter unchanged.

### Resumption notes

The renderer ABC is the load-bearing piece. Once it exists, Step 9
(OpenGL) plugs in as a third subclass with no further refactoring.
If `wx.GraphicsContext` shadow support is missing on the target
build, the manual-offset fallback above works everywhere.

---

## Step 9 — OpenGL board renderer

**Status:** not started; gated on Step 8 landing.

**Goal:** A 3D board view alongside Text and Graphics in
`View → Board Style`. Cylindrical pegs, disc geometry with normals,
perspective camera, basic Phong lighting.

**Why gated on Step 8:** Phase 1 (Step 8) validates the renderer-
swap architecture and the menu UX. If that boundary is wrong, the
heavier OpenGL path surfaces it more painfully. Land Step 8 first.

**Why it's worth doing at all:** Bill's domain professionally, and a
Hanoi viewer that looks like one of the MVP demos doubles as a
teaching artifact for modern OpenGL on its own.

### Tasks (rough — refine when Step 8 is done)

- [ ] `GLBoardRenderer(BoardRenderer)` using `wx.glcanvas.GLCanvas`
      + `wx.glcanvas.GLContext` (PyOpenGL already available).
- [ ] Cylindrical pegs as triangle-strip meshes; copy the cylinder
      helper pattern from mvpVisualization rather than importing
      it (this is a hanoi project, not a cross-project link).
- [ ] Disc geometry: short cylinders with top/bottom caps and a
      per-disc color uniform.
- [ ] Perspective camera tilted slightly so discs read as 3D;
      orthographic fallback is OK if perspective setup eats time.
- [ ] One directional light; per-vertex normals; basic Phong shader.
- [ ] Core-profile boilerplate: VAO, VBO, shader program,
      glDrawArrays. macOS gotchas don't apply here (Fedora target),
      but if Bill ever runs this on Apple, the always-bound VAO and
      no-validate-with-multi-samplers patterns from existing memory
      are the answer.
- [ ] No animation in v1; `update()` triggers a full re-render.
- [ ] `View` menu gains a third radio item `OpenGL`.
- [ ] Smoke-test under X-forwarding: GL context creates; state
      matches Text/Graphics views; menu radio behavior unbroken.

### Risks specific to OpenGL

- **GL context under X-forwarding** is the known soft spot in the
  container workflow. If `wx.glcanvas` can't create a context, log
  the error and grey out the menu item — no clever fallbacks.
- **Mesa quirks** — multiple existing memories
  (`feedback_mesa_image_load_store`, `feedback_query_uniform_locations`)
  document past Mesa-vs-real-driver divergences. They almost
  certainly don't bite a basic-geometry-and-lighting renderer, but
  the playbook is in those notes if they do.

### Out of scope

- Disc-move animation (a possible Step 10).
- Click-to-move via pick buffer (a possible Step 11).
- Textured discs / shadow mapping / fancy lighting.

---

## Cross-cutting items (do whenever they fit)

- [ ] Fix `[tools.ruff]` typo in `pyproject.toml` (should be `[tool.ruff]`).
- [ ] Tick off `TODO.org` UI helper unit tests once they move to the
      presenter (step 1 makes them testable).

---

## What's left

Steps 1–7 are implemented (5 signed off; 6 and 7 awaiting smoke-test).
Optional follow-on work, in roughly descending order of value:

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
