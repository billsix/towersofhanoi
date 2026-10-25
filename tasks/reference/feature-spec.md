# hanoi — feature specification (UI-independent)

**What this is:** the definition of what the hanoi program *is* and *does*, independent of any user
interface or implementation language. It states the rules, the domain concepts, and every feature — for
each: what the user can do, what the UI must show, and **why** (the teaching intent). UI-category advice
(TUI/CLI and GUI) follows at the end, and a per-implementation **compliance checklist** closes the doc.

**Authority:** extracted from the **Python package** `python/src/hanoigame/` (the behaviour oracle; see
the repo-root `CLAUDE.md`). Where this spec and the Python code disagree, that is a bug in one of them to
reconcile — the spec and Python are kept in step; the Rust, C++, and bash implementations conform to this
spec. Written 2026-10-25 (William Emerison Six <billsix@gmail.com>). This is a reference doc — updated in
place, never archived.

## 1. Purpose & teaching intent

hanoi is a **teaching program**. The goal is not recursion for its own sake but learning to solve the
puzzle **by hand via peg relabelling**: solve a small stack, then reuse that solution as a black box for
a bigger stack by relabelling the pegs ("solve small, relabel, replay"). **Every feature serves that
idea** — especially recipes (save a solve), relabelling (rename the pegs), and the rebinding display
(see the relabelling made concrete when a recipe is replayed). A UI that omits the relabelling/recipe/
rebinding features is not a hanoi UI in this sense, even if it can solve the puzzle.

## 2. The rules of Towers of Hanoi

- Three **pegs** and **N disks** of distinct sizes. The game starts with all N disks on the **first**
  peg, largest on the bottom, smallest on top.
- A **move** takes the **top** disk off one peg and places it on another peg. A move is **legal** only
  if the destination peg is empty or its top disk is **larger** than the disk being moved (never a larger
  disk onto a smaller one).
- The game is **won** when all N disks are stacked on the **third** peg.
- The **optimal** solution takes `2^N − 1` moves (shown as a target, not enforced).

(Source: `hanoimodel.py` — `HanoiGame`, `move_options`, `check_win_condition`; `engine.min_moves`.)

## 3. Domain concepts (UI-independent vocabulary)

- **Physical pegs.** The three pegs have fixed physical positions (internally 0,1,2). The start peg is
  physical peg 1, the goal peg is physical peg 3 (1-indexed as the user sees them).
- **Labels and the six labellings.** The pegs the user *sees* are 1-indexed **labels**. A **labelling**
  assigns the labels 1,2,3 to the three physical pegs — there are **six** (every permutation of 1,2,3).
  The **default** labelling is `1,2,3` (label = physical position). Relabelling changes which label sits
  on which physical peg; it never moves disks. (Source: `presenter.Labelling`.)
- **Colour follows the label, not the peg.** When a UI colours the pegs, the colour tracks the *label*
  (label 1 / 2 / 3 keep their colour across a relabel), so the student can keep tracking "label 1 is the
  blue peg" after relabelling. (Source: `presenter._PEG_COLOR_BY_LABEL`, `peg_color`.)
- **Default-label space.** Moves are recorded and stored as **physical** peg pairs (1-indexed = the
  default labelling), independent of whatever labelling was active when they were made. (Source:
  `recipe` module docstring; `engine._handle_move` records `fp+1, tp+1`.)
- **Recipe.** A saved, named sequence of moves (in default-label space) plus the disk count it solves.
  (Source: `recipe.Recipe`, `Recorder`, `RecipeRegistry`.)
- **Rebinding.** When a recipe is replayed under a **non-default** labelling, each move in the recipe's
  own labels maps to a **physical** peg — the **rebinding** (recipe's labels → physical pegs). The
  recipe's moves expressed on the physical pegs are the **rebound moves**. The default labelling has no
  rebinding to show. (Source: `recipe.rebinding`, `rebound_moves`, `format_rebinding_table`.)

## 4. Features — what the user can do

Each feature lists *what it does*, what the UI must let the user **see**/**do**, and **why**.

### 4.1 Start a game with a chosen disk count
- **Does:** begins a fresh game with N disks, all on the start peg, default labelling, empty move count.
- **See:** the initial board. **Do:** choose N (a positive disk count).
- **Why:** small N first is the whole method — you solve N, then relabel and reuse it for N+1.

### 4.2 Make a move
- **Does:** moves the top disk from one labelled peg to another, if legal; increments the move count;
  records the move (in default-label space).
- **See:** the updated board and move count; on an **illegal/invalid** move, a reason — distinct messages
  for: label out of range, source == destination, source peg empty, and "larger on smaller" (naming the
  two disks). (Source: `commands._move_or_error`, `engine._handle_move`.)
- **Do:** specify a from-peg and a to-peg **in the current labels**.
- **Why:** the player drives the solve; clear rejection reasons teach the legal-move rule.

### 4.3 Relabel the pegs
- **Does:** sets the current labelling to a chosen permutation of 1,2,3 (physical pegs 1,2,3 now show as
  a,b,c). Disks do not move.
- **See:** confirmation of the new labelling; thereafter the board's label row shows the new labels **and**
  a reference row showing the physical 1,2,3 underneath (so both are visible). (Source: `presenter.render`
  default-reference row; `engine._handle_relabel`.)
- **Do:** pick a labelling (a permutation of 1,2,3); a non-permutation is rejected with a reason.
- **Why:** relabelling is the mechanism that lets a solved sub-problem be reused — the core lesson.

### 4.4 View valid moves
- **Does:** reports the currently legal moves, expressed **in the current labels**, sorted.
- **See:** the list of legal moves (or "no valid moves"). (Source: `engine.valid_moves_str`.)
- **Why:** scaffolds the learner without solving it for them.

### 4.5 Record and save a recipe
- **Does:** every legal move (typed or applied) is recorded; **after a win**, the move sequence can be
  **saved** under a name as a recipe (with its disk count). Saving under an existing name overwrites it
  (reported). Saving is only meaningful after winning. (Source: `Recorder`, `engine.save_recipe`; `save`
  dispatched mid-game returns the "only works after winning" guidance.)
- **See:** a save confirmation (or overwrite notice); the prompt/affordance to name a recipe on winning.
- **Do:** name and save the just-won solution.
- **Why:** a saved small solve is the black box you replay (under a relabelling) to solve a bigger one.

### 4.6 List recipes
- **Does:** lists every saved recipe with its disk count and move count. (Source: `engine._handle_list`.)
- **See:** the saved recipes (or "none yet"). **Do:** request the list.

### 4.7 Show a recipe
- **Does:** prints a named recipe's moves in order (in default-label space), with its disk/ move counts.
  (Source: `engine._handle_show`.) **See:** each step `from -> to`. **Do:** name the recipe.
- **Why:** inspect the stored solution independent of replaying it.

### 4.8 Apply (replay/invoke) a recipe — the rebinding moment
- **Does:** replays a named recipe's moves **translated through the current labelling**, applying each to
  the board (recording the applied moves), stopping with a reason if a step is illegal in the current
  state. (Source: `engine._handle_apply`, `recipe.apply_iter`.)
- **See — and this is the parity-critical part:**
  1. the **recipe** being invoked (its moves),
  2. the **rebinding** — the recipe's own labels → the physical pegs they map to under the current
     labelling (shown only when a non-default labelling is active; the default has no rebinding),
  3. the **rebound move set on the global/physical pegs** — the recipe's moves expressed on the physical
     pegs,
  4. a per-step log and a final "Done" / "stopped — <reason>".
  These three — recipe moves, the label→peg rebinding, the rebound physical moves — are the **three-panel
  rebinding view** (`recipe.format_rebinding_table`: `<left_header> | Rebinding (label -> peg) | Rebound
  (physical pegs)`).
- **Do:** name a recipe to invoke under the current labelling.
- **Why:** this is where the relabelling method becomes concrete — the learner *sees* their small solve,
  under the current renaming, become the moves that advance the bigger puzzle. (Rationale:
  `tasks/archive/2026/09/14/record-recipe-bindings-and-show-rebinding.md`.)

### 4.9 Win detection
- **Does:** detects the win (all disks on the goal peg) and surfaces it (with the move count vs. the
  optimal `2^N − 1`). **See:** that the game is won + the counts. **Why:** closes the solve and gates the
  save-recipe affordance.

### 4.10 Help and quit
- **Help:** show the command/feature reference. **Quit:** exit. **Empty input:** redraw / re-prompt, no
  state change. (Source: `commands.HELP_TEXT`, `engine.dispatch`.)

## 5. What a UI must SHOW (summary)

A conformant UI must be able to present: the **board** (pegs + disks); the **current labelling** on the
pegs, with the physical 1,2,3 reference visible when relabelled; the **move count** (and the optimal
count); the **legal moves** in current labels; the **recipe list**; a recipe's **moves** (show); the
**three-panel rebinding view** on apply (recipe moves | rebinding label→peg | rebound physical moves);
the **win** state; and **rejection reasons** for illegal input. Colour, where used, follows the label.

## 6. UI-category guidance (advice, not core)

These are recommendations for *how* a category of UI presents the features above; the features and the
"what it must show" list are mandatory, the presentation is not.

### 6.1 TUI / CLI (terminal)
- A **command grammar** drives everything: moves as `<from> -> <to>` (also accept `1 3` and `13`), and
  the verbs `relabel a b c`, `save <name>`, `apply <name>`, `show <name>`, `list`, `help`, `quit`
  (`quit`/`q`/`exit`, `help`/`h`/`?`). (Source: `commands.parse`, `HELP_TEXT`, `COMMAND_VERBS`.)
- **Tab-completion** of the command verbs and saved-recipe names where the terminal supports it; keep
  `COMMAND_VERBS` the single source so completion can't drift from the grammar.
- Render the board and the three-panel rebinding as **aligned text columns**
  (`format_rebinding_table`); after a single move under a relabelling, a text UI may print that one move's
  rebinding inline (`engine.move_teaching_lines`). Keep a **plain stdin/stdout** mode usable by screen
  readers (no curses required).

### 6.2 GUI (windowed)
- Group actions on a **menubar**: a Game menu (new game / disk count, quit), a Relabel menu (the six
  labellings), a Recipe menu (save / list / show / apply). Keep action controls **stable** — e.g. show
  all move buttons and **disable** the illegal ones rather than hiding them, so controls don't jump.
- Present the **three-panel rebinding view** as three side-by-side panels/lists (recipe moves | rebinding
  | rebound physical moves), not only as text.
- An **illegal move** is surfaced as a dialog, not folded into the board redraw. (Source: the GUI
  treats a non-empty move result as an error — `engine.move_teaching_lines` docstring.)
- Colour the pegs by **label** (so colour tracks a label across relabels). Offer the save-recipe
  **prompt on winning**. A 2D-graphics board or a text board are both acceptable.

## 7. Compliance checklist (per implementation / UI)

Audit any implementation or new UI against these rows. Mark each: **✓** (present), **partial**, **✗**
(absent), or **n/a** (justified — e.g. a non-interactive educational script).

1. Three pegs, N disks, correct start position.
2. Legal-move rule enforced (never larger-on-smaller; never from empty).
3. Win detection (all on the goal peg) + move count + optimal `2^N−1` shown.
4. Make a move in the current labels; distinct rejection reasons (range / same peg / empty / larger-on-smaller).
5. The six labellings; relabel to any permutation; relabel never moves disks.
6. Board shows the current labelling + the physical 1,2,3 reference when relabelled.
7. Colour (if any) follows the label, not the physical peg.
8. Valid-moves display in current labels.
9. Record moves in default-label space; save a recipe (post-win) with a name + disk count; overwrite reported.
10. List recipes (name, disk count, move count).
11. Show a recipe's moves.
12. **Apply a recipe under the current labelling** — applies to the board, records, stops-with-reason.
13. **The three-panel rebinding view on apply** — recipe moves | rebinding (label→peg) | rebound physical
    moves; rebinding shown only under a non-default labelling.
14. Help/quit/empty-input behavior (interactive UIs).

## Python conformance (the authority) — reconciled 2026-10-25

The Python package implements all of §§2–6 and nothing beyond it that this spec omits: the command set
(`commands.parse`/`HELP_TEXT`) is exactly move/relabel/save/apply/show/list/help/quit (+ empty/error);
dispatch (`engine.GameSession.dispatch`) has one handler each; the board, labelling reference row, valid
moves, move count, optimal count, rebinding table, and colour-by-label are all present and are all
captured above. No Python behavior was found that is not represented in this spec (so nothing was flagged
as cruft, and nothing was added to the spec beyond Python). The three front-ends (`hanoicli`,
`hanoigame`, `hanoigui`) are UI-category evidence for §6, not additional core.

## Other implementations — compliance (audited 2026-10-25)

Summary (full per-row table + gaps: `tasks/program-feature-spec-and-compliance.md` § Audit results):

- **Rust** — the shared `hanoigame` crate implements the full spec (all recipe/rebinding/three-panel
  logic, unit-tested); the only gaps are presentation-layer in two front-ends: the **Tauri** app shows no
  three-panel view on apply (§4.8) and the **ratatui TUI** shows no valid-moves line (§4.4), plus weak
  help in wx/Tauri. → `tasks/rust-feature-parity-tauri-tui-gaps.md`.
- **C++** — the engine has the rules + `rebinding()`, but the ImGui GUI lacks the §4.8 three-panel view,
  §4.7 show-recipe, apply-records-moves, and several smaller items (optimal count, physical reference row,
  distinct rejection reasons, overwrite report, save-gated-on-win, help/quit).
  → `tasks/cpp-add-wx-frontend-and-recipe-view-parity.md` Part B.
- **bash** — a by-design non-interactive demo of the relabelling method (solve scripts composed through
  six `tr` relabel filters); embodies §3/§4.3 relabelling cleanly but is not a game UI, so most
  interactive rows are n/a. Not a parity target.

## Related

- Authority: `python/src/hanoigame/` (`hanoimodel`, `presenter`, `recipe`, `commands`, `engine`, the
  three front-ends, `board_renderers`).
- `tasks/reference/architecture-overview.md` — the dispatch data-flow + the default-label-space invariant.
- `tasks/archive/2026/09/14/record-recipe-bindings-and-show-rebinding.md` — the rebinding teaching moment.
- Spec-driven parity tasks: `tasks/cpp-add-wx-frontend-and-recipe-view-parity.md`,
  `tasks/rust-gui-use-shared-xrc.md`; the audit + process: `tasks/program-feature-spec-and-compliance.md`.
