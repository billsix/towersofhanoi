# Win celebration & recipe discovery — the UX design (and why)

**Reference document.** How every hanoi front-end handles the **win moment** — congratulating the
player, teaching that *recipes* exist, and offering to save the solution — and **why** it is shaped this
way. Grounded in the Apple-HIG principles in `tasks/reference/ui-design-principles.md`; this doc is the
specific flow for the win → teach → save experience. Not a task; update in place. Created 2026-11-01
(William Emerison Six <billsix@gmail.com>).

## The domain in one paragraph (for a reader new to it)

hanoi teaches solving Towers of Hanoi **by hand** via "solve small, relabel, replay": solve a small
stack, **save** that solution as a named **recipe**, then **relabel** the pegs and **replay** (apply) the
recipe to solve a bigger stack. A novice does not know this method exists. The three features that embody
it — **recipes** (save a solve), **relabelling** (rename the pegs), and the **rebinding view** (the
three-panel picture shown when you replay a recipe under a relabelling: *recipe moves | label→peg |
rebound physical moves*, `feature-spec.md` §4.8) — are the payoff. The UI must **teach that these exist**,
because a learner who already knew the method would not need the program.

## The problem this solves

Winning is the natural **teaching hinge** — the first moment recipes make sense (you can only save a
solution after producing one). Two earlier designs failed:

1. **Silently** enabling the Relabel/Recipe menus at the first win — a novice never notices a menu quietly
   un-graying, so they never discover recipes. (The original bug this whole effort fixes.)
2. A win-celebration **modal** that congratulated + taught + offered **Save**, shown on **every** win —
   this **collided** with the rebinding view: a recipe-apply (or a relabelled move) that happens to *win*
   popped the rebinding teaching window **and** the celebration modal at once. Two teaching surfaces
   fighting for attention is confusing. (Found in the wxPython display-verify, 2026-11-01.)

## What we chose (it differs by UI category — deliberately)

### Graphical UIs — wx (Python/Rust/C++), egui, ImGui, the Tauri webview

- **First win → a teaching modal.** Congratulate, and teach the method in plain words ("save this
  solution as a recipe and replay it on a new game — even a bigger one, by relabelling the pegs"). **No
  Save button here** — just acknowledge. Crucially, the **first win is always a clean hand-solve under the
  default labelling** (you cannot relabel-win or apply-win before your first win), so this modal **never**
  collides with the rebinding view.
- **Later wins → a lightweight status line only, no window.** The player already learned the method; a
  second modal is exactly the thing that collided with the rebinding view, so later wins just say "Solved
  in N moves!" in the status area. **No competing window.**
- **Save is offered when the solution is about to be discarded** — when the player starts a **New Game**
  (also New Game (Same Size) and a disc-count change): *"Save your solution as 'solve-N' before starting
  over?"* This is the familiar **save-before-you-close** pattern, at a calm moment with nothing else on
  screen. It is **suppressed** when the finished solution was produced by **replaying a recipe** (nothing
  new to save) or was **already saved** from the Recipe menu.

### Text UIs — plain CLI, curses TUI

A terminal prints top-to-bottom with no overlapping windows, so it has more room and no collision: it
shows **everything in sequence** at the win — the rebinding table (if relabelled), the congratulation,
and the **save prompt** (prefilled `solve-N`, editable). The text UIs therefore keep offering the save
**at the win itself**. This is a deliberate divergence from the GUIs, allowed because `feature-spec.md` §6
makes presentation a per-category choice while the *features* stay mandatory.

## Why this shape (the principles)

- **Teach once, at the hinge** (knowledge-of-your-audience; progressive disclosure): the recipe concept is
  taught at the first win and not re-taught afterward.
- **Don't over-modal / modelessness** (Apple HIG): a modal on every win is intrusive and — here — collides;
  reserve the modal for the one moment it actually teaches.
- **Save-before-discard**: a well-understood pattern; moving the save to the New-Game boundary takes it
  out of the crowded win moment **without losing it**.
- **Perceived stability / dim-don't-remove**: the Tier-2 menus still *enable* at the first win (unchanged);
  the celebration explains what just became available, rather than relying on the player noticing.
### Alternatives considered (and why save-at-discard won)

1. **Suppress the celebration when a rebinding window is shown** — removes the collision, but also drops
   the congratulation and the save offer on those wins.
2. **Sequence the celebration after the rebinding window closes** — keeps it on every win, but adds a
   second window to dismiss and is awkward in the immediate-mode GUIs (egui/ImGui have no close event).
3. **Merge a "Solved! Save?" footer into the rebinding window** — one window, but invasive (the rebinding
   layout is a shared XRC/panel) and only helps the relabelled case.
4. **Make the celebration a non-modal in-window banner** — never competes as a window, but loses the
   deliberate "stop and notice" modal that works well for a clean win.
5. **(chosen) Move the save to the new-game / discard boundary** — removes the collision at the source:
   the win moment carries teaching only (and only on the first win), and the save happens later at a calm
   boundary. The full options log is
   `tasks/archive/2026/11/01/win-celebration-rebinding-collision.md`.

## The shared mechanism (how it is built)

- **Wording** is one core helper per language — `presenter.format_win_celebration(num_disks, moves,
  min_moves, first_win)` plus `default_recipe_name(n) → "solve-<n>"` — mirrored from the Python oracle
  **string-for-string** (each port asserts the exact lines in a test). The helper returns the
  congratulation + result, plus the teaching lines only when `first_win` is true.
- Each GUI tracks two bits of per-game state, both reset on a new game: whether the current won solution
  was **reached by applying a recipe** (→ suppress the save offer) and whether it has **already been
  saved** from the Recipe menu (→ don't re-offer). At each discard point the save is offered iff
  `won && !reached_by_apply && !already_saved`.
- **Caveat:** a player who wins and then **quits** (never starts a new game) is not offered the save —
  recipes are a teaching convenience, not precious data, so this is acceptable.

## Cross-links

- `tasks/reference/ui-design-principles.md` — the Apple-HIG grounding + the three-tier learning flow (the
  win is the Tier-2 hinge).
- `tasks/reference/feature-spec.md` — §3.5 (learning flow), §4.5 (save a recipe), §4.8 (rebinding view),
  §4.9 (win), §6 (per-category presentation).
- `tasks/archive/2026/11/01/win-celebration-recipe-discovery.md` (+ the python/rust/cpp children) — the implementation;
  `tasks/archive/2026/11/01/win-celebration-rebinding-collision.md` — the options log for this decision.
