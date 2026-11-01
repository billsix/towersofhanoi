# hanoi — UI design principles (Apple HIG-grounded)

**Reference document** — the user-interface design philosophy every hanoi front-end conforms to,
grounded in Apple's classic Human Interface Guidelines and specialized to this teaching program. It
states the principles and the resulting information architecture (what is **true** of a conformant
hanoi UI); the *what-features-exist* authority is `tasks/reference/feature-spec.md`, and the
*how-to-implement-it* lives in the task docs. Not a task; update in place. Created 2026-10-31
(William Emerison Six <billsix@gmail.com>).

## Why this doc exists

hanoi is a teaching program for a user who **does not already know how to solve Towers of Hanoi** and
who learns by **incremental discovery** (`feature-spec.md` §1). That makes UI design a first-class
concern, not decoration: the interface itself must teach the method ("solve small, relabel, replay"),
because a learner who already knew the method wouldn't need the program. The design standard is
Apple's classic **Human Interface Guidelines** — user-centered, recognition-over-recall, progressive
disclosure — because its whole premise is designing around the *user's* mental model and task, rather
than the *program's* data model. The earlier hanoi UIs were organized around the domain model
(recipes, labellings, rebinding all surfaced at once); this doc records the correction to a
learner-journey architecture.

### The Apple source

- *Apple Human Interface Guidelines: The Apple Desktop Interface*, Apple Computer / Addison-Wesley,
  **1987** — origin of the first principles (metaphor, direct manipulation, see-and-point,
  consistency). Scan:
  <https://andymatuschak.org/files/papers/Apple%20Human%20Interface%20Guidelines%201987.pdf>
- *Macintosh Human Interface Guidelines*, Apple Computer, **1992** — the fuller principle set used
  here (adds user control, feedback and dialog, forgiveness, perceived stability, aesthetic integrity,
  modelessness, and "knowledge of your audience"). Scan:
  <https://archive.org/download/inside-macintosh-1992-1994/1992-human_interface_guidelines.pdf>

The 1992 Chapter 1 principle order, verbatim from Apple's own table of contents: Metaphors, Direct
Manipulation, See-and-Point, Consistency, WYSIWYG, User Control, Feedback and Dialog, Forgiveness,
Perceived Stability, Aesthetic Integrity, Modelessness, then *Additional Issues* including Knowledge
of Your Audience.

## The principles that govern hanoi, and how each applies here

- **Knowledge of your audience (the governing one).** The audience is a novice who does not know the
  rules or the method. The UI must therefore *teach by being used*: state the goal and the one legal
  move rule on screen, and reveal advanced concepts only when the learner has a reason to want them.
  Never assume prior knowledge of Hanoi or of the relabelling trick.
- **See-and-point (recognition over recall).** The learner should *recognize* available actions on
  screen, not recall a command vocabulary. Legal moves and next steps must be visible, not memorized.
  (The CLI's verb grammar is a concession to the terminal, not the target experience — even there, a
  valid-moves display and tab-completion keep it recognition-first.)
- **User control + modelessness.** The user initiates and sequences actions; the program never locks
  them into a rigid order. Progressive disclosure (below) is *not* a wizard or a locked mode — Tier-2
  features become *available and obvious* after the first win, they are not forced.
- **Feedback and dialog.** Every action gets a visible response, and the learner always knows what
  they just did and where they stand. The **move history** and the live **move count vs the optimal
  `2^N−1`** are the primary feedback artifacts and must be first-class, not buried.
- **Perceived stability.** A stable visual framework that does not rearrange under the user. The
  textbook rule is **dim, don't remove**: an unavailable action is disabled/greyed, never deleted, so
  the layout stays put. (hanoi already does this — the GUI shows all move buttons and disables the
  illegal ones; keep it. A Tier-2 feature revealed after a win should *enable*, not pop into
  existence in a way that shifts the board.)
- **Forgiveness.** Moves are cheap and the puzzle is restartable, so the UI should *encourage
  exploration* — the learner discovers the legal-move rule by trying moves and reading clear rejection
  reasons, not by reading a manual.
- **Consistency.** All six implementations present the *same* flow and hierarchy, enforced by the
  single feature-spec oracle (Python is the behavior authority). This doc's tiers are part of that
  shared contract, so the learning experience is the same in every language/UI.
- **Direct manipulation + metaphor.** The board is the real object; disks and pegs are manipulated
  directly where the medium allows. The three-panel rebinding view (`feature-spec.md` §4.8) is the
  design's showpiece — it makes the otherwise-invisible relabelling concept *visible*.

## The core design decision: three tiers of progressive disclosure

The information architecture is keyed to the **learner's journey**, not the domain model. Every
conformant hanoi UI organizes its features into three tiers:

- **Tier 1 — the core workspace, ALWAYS visible.** The board; a one-line statement of the **goal**;
  the **move history** (numbered, in default 1-2-3 / physical labelling, with a live count vs the
  optimal `2^N−1`); and legal/illegal-move feedback. This is the novice's entire world during the
  first solve, and it is sufficient to play and win with zero knowledge of recipes or relabelling.
- **Tier 2 — revealed at the moment it becomes meaningful (after the first win).** Relabelling and
  recipes. These are noise during the first solve (a recipe can only be saved *after* a win —
  `feature-spec.md` §4.5 — and relabelling has no motivation until you have a solved stack to reuse).
  The **win is the teaching hinge**: on winning, the UI offers the next step — save this solution,
  start a larger stack, and reuse the saved solve under a relabelling. Tier-2 affordances *enable*
  (dim→active) at that point; they are available thereafter, never forced.
- **Tier 3 — advanced / reference, out of the main workspace.** Recipe list / show / apply and the
  three-panel rebinding table. Present and discoverable, but never competing with the board: a
  **menu** in a GUI, a **secondary tab or toggled panel** in a TUI.

## Rulings a conformant hanoi UI must follow

1. **Move history is an always-visible panel**, not an on-demand dialog. (The wxPython oracle's
   original Ctrl+H dialog, `feature-spec.md` §4.11, is superseded by an always-visible panel; the
   menu item may remain as an alternate way to focus it.) Content is unchanged: the numbered
   default-label-space list from `presenter.format_move_tally`, live count, moves-only, reset per game.
2. **Recipes live in Tier 3** — a menu in a GUI, a tab/toggled panel in a TUI — not surfaced during
   the first solve. *Realized in the wxPython oracle:* each saved recipe is a **submenu → View /
   Apply** (point at the recipe, not an abstract "Apply…/Show…/List…" verb that pops a chooser), with
   **Save** the menu's first item (Ctrl+S), dimmed until the first win.
3. **Relabelling is gated into Tier 2** — not a permanent top-level offering. It is introduced at the
   first-win moment (the handoff to reusing a solved stack), and remains available afterward.
4. **Onboarding for the non-knower** — an always-present one-line **goal statement**, plus a
   dismissible **"How to play"** (the rules + the one legal-move rule + the "solve small, relabel,
   replay" idea). Implicit teaching is not enough for an audience that does not know the puzzle.
   *Realized across the GUIs:* the goal line sits in the **status bar** (terse, out of the board's
   way); "How to play" is a **centered modal dialog** shown once on first run (centered in the middle
   of the window, not an inline panel pinned above the board) and reopenable from the **Help** menu,
   with a ✓/✗ legal-move diagram (not a screenshot) and a "don't show again" preference. (wx/ImGui use
   a native modal; egui a centered window; Tauri an HTML `<dialog>` `showModal`.) A terminal UI prints
   the same text on first run / on `help`.
5. **Preserve what already matches the HIG** — dim-don't-hide for illegal actions (perceived
   stability), colour-follows-label (`feature-spec.md` §3), and the three-panel rebinding view as the
   direct-manipulation showpiece of the method.
6. **The shared wx layout (`ui/hanoi.xrc`) stays structural; each wx front-end wires the flow in
   code.** The three wx front-ends (wxPython oracle, C++ wxWidgets, Rust wxDragon) load the *same*
   `ui/hanoi.xrc`, so the tier structure is **not** baked into the XRC: each hides/ignores the XRC
   recipe sidebar and builds the Recipe menu, history panel, goal line, and How-to-Play panel
   programmatically. This keeps the XRC a stable shared contract — baking the tiers in would force
   reworking all three front-ends at once and risk regressing them together — and lets each adapt to
   its toolkit's limits (e.g. wxDragon builds its menu bar in code, since it has no runtime
   menu-insert on an XRC-loaded `MenuBar`, and *hides* rather than destroys the sidebar, since it has
   no sizer detach). *(Decided William Emerison Six <billsix@gmail.com>, delegated 2026-11-01;
   confirmed by the oracle, which already works this way on the unchanged XRC.)*
7. **Direct manipulation: drag a disc, and keep the buttons.** Every graphical front-end lets the
   player drag a peg's top disc onto another peg — **nearest-peg targeting** (forgiving), an illegal
   drop **snaps back** with the usual rejection reason, dragging is **off once solved** — *and* keeps
   the move buttons as the keyboard/accessible path (two affordances for one action, not a choice).
   The drop resolves to a `<from>→<to>` move dispatched through the **same shared core** as a button
   (one dispatch path), so the rule lives in the core, not the gesture. Per-toolkit mechanics differ
   (immediate-mode frameworks track the drag across frames; retained-mode wx captures the mouse; the
   Tauri webview uses canvas pointer events) but the behaviour is identical. *(Approved as a wxPython
   spike, then fanned out to all five graphical UIs, 2026-11-01.)*

## Relationship to the feature spec

`feature-spec.md` defines **what** features exist and what each must show; **this** doc defines the
**flow and hierarchy** they are presented in (which tier, revealed when). The spec's §6 UI-category
guidance (TUI vs GUI presentation) is refined by the tiers above. When the two are updated together,
the spec gains a "Learning flow / progressive disclosure" section that points here, and this doc
stays the rationale (the *why*, grounded in the Apple HIG).

## Cross-links

- `tasks/reference/win-celebration-and-recipe-discovery-ux.md` — how the **win moment** teaches recipes
  and offers the save (first-win teaching modal; later wins lightweight; GUI save deferred to the
  new-game boundary to avoid colliding with the rebinding view), and why.
- `tasks/reference/feature-spec.md` — the UI-independent feature definitions (the *what*); its §1
  teaching intent and §4.11 move tally motivate tiers 1–2, its §4.8 rebinding view is the Tier-3
  showpiece.
- `tasks/reference/architecture-overview.md` — the shared dispatch data flow and the
  default-label-space invariant the move history and recipes rest on.
- `tasks/reference/per-language-subproject-layout.md` — the per-language template the tiers are
  implemented across (the consistency guarantee).
