# Win celebration + recipe discovery — realize the "teaching hinge" on winning (umbrella)

**Status:** proposed — needs go-ahead (umbrella; children are the per-language tasks below).
**Priority:** 4 **Difficulty:** 6 (spans 3 languages × many UIs)
**Created:** 2026-11-01 (William Emerison Six <billsix@gmail.com>). From the maintainer's observation that
a player who wins **doesn't learn that recipes exist** — the UIs quietly enable the Tier-2 menus, but a
novice never notices, so the program's whole point ("solve small, relabel, replay") goes undiscovered.

## BLUF

When a player wins today, most UIs merely **enable** the Relabel/Recipe menus (dim→active) — a passive
change a first-time winner won't see. The spec already calls the win **"the teaching hinge"** that should
**"offer the next step — save this solve, start a larger stack, reuse it under a relabelling"**
(`tasks/reference/feature-spec.md` §3.5, §4.5, §4.9; `ui-design-principles.md` §"Tier 2"), but that intent
is only weakly realized. This initiative makes **every** hanoi UI, on winning, show an explicit
**congratulatory + recipe-teaching moment**: *you solved it in M moves (optimal or not), and you can **save
this solution as a recipe** and **replay it on a new game** — even a bigger stack, by relabelling the
pegs.* "Done" = all UIs across **Python, Rust, C++** surface it consistently, the wording lives in each
language's **core** (not per-UI copy), and the **feature-spec + compliance checklist** are updated. Python
(the behaviour oracle) goes first and fixes the canonical wording; Rust and C++ mirror it.

## Context (read first)

- **Design authority:** `tasks/reference/ui-design-principles.md` (Apple HIG; the three-tier flow — the
  **win is the teaching hinge**, §"Tier 2 / revealed at the first win") and
  `tasks/reference/feature-spec.md` §3.5 (learning flow), §4.5 (save a recipe — the **save prompt on
  winning**, default name `solve-<N>`), §4.9 (win detection), §6.2 (GUI: "offer the save-recipe prompt on
  winning").
- **What exists today (the partial realization to build on):** the Rust **Tauri** frontend already shows
  an inline line on win — "Solved in M moves — … Save it from the Recipe menu to keep it"
  (`rust/tauri/frontend/main.js` `render()`). That is the right idea but passive and Tauri-only; most
  other UIs just flip the menus from disabled to enabled. This initiative makes the moment **explicit and
  consistent** everywhere.
- **The behaviour oracle is Python.** `python/src/hanoigame/` — `presenter.py` (shared text helpers like
  `format_move_tally`), `engine.py` (win/optimal/save), and the three front-ends `hanoicli.py`,
  `hanoigame.py` (curses TUI), `hanoigui.py` (wxPython GUI). Wording decided here flows to the spec and to
  Rust/C++.

## The cross-cutting design (write once here; children implement per toolkit)

**What the moment says — three parts:**
1. **Congrats + result.** "Solved in M moves." + an optimal verdict: if `M == 2^N−1`, "Optimal — the
   fewest possible for N discs!"; else "the minimum for N discs is K."
2. **The teaching line (the point).** You can **save this solution as a recipe** and **replay it on a new
   game** — including a **bigger** stack, by **relabelling** the pegs ("solve small, relabel, replay").
3. **The affordance (offer, don't force — HIG user control).** Save now, with the name **prefilled
   `solve-<N>`** (§4.5), or where to find it later (the Recipe menu / the `save` command).

**When it shows (HIG modelessness / forgiveness — don't over-modal):**
- **First win of the session** = a prominent one-time teaching moment (a GUI **modal** like "How to
  play"; a printed block in CLI/TUI). This is where parts 2–3 teach the recipe concept.
- **Later wins** = a **lighter** congratulatory line (the existing inline message), not a re-teach and not
  a forced modal.

**Where the logic lives (the maintainer's "core if needed, or each UI"):** a **shared core/presenter
helper per language** returns the celebration text from the snapshot (`won`, `moves`, `min_moves`, and a
"first win this session" flag), so every UI in that language renders **identical wording** and stays thin.
Only the **presentation** (modal vs banner vs printed block) is per-UI — matching the move-tally fan-out,
where `presenter.format_move_tally` was the one shared string.

**Preserve the existing gating.** The Tier-2 enable (dim→active) still happens (perceived stability); the
celebration *explains* it. Dragging is already off once won (`ui-design-principles.md` ruling #7).

## Children (per language; Python first, the other two mirror it)

- **Python (oracle — do first):** `tasks/win-celebration-recipe-discovery-python.md` — the core helper,
  the three Python front-ends, and the **feature-spec + compliance-checklist** update.
- **Rust (depends on Python):** `tasks/win-celebration-recipe-discovery-rust.md` — mirror the helper into
  the `hanoigame` crate; wire all five front-ends (cli, ratatui TUI, wxDragon, **Tauri — upgrade the
  existing inline hint**, egui).
- **C++ (depends on Python):** `tasks/win-celebration-recipe-discovery-cpp.md` — mirror into the
  header-only core; wire the ImGui GUI (native + wasm) and the wxWidgets GUI.

Ordering is **Priority + "Depends on"**, not `blocked` (each language is within our control once the
wording is fixed). Rust and C++ can proceed in parallel after Python.

## Open questions (block implementation; each has a recommendation — answer by number)

1. **Trigger:** first-win-only teaching modal + lighter inline on later wins, **or** the full moment every
   win? **Recommend (a) first-win modal + inline after** — HIG says teach once, don't over-modal (mirrors
   "How to play" shown once).
2. **Does the first-win GUI popup offer Save directly** (a "Save as recipe" button prefilled `solve-<N>`,
   merging §4.5's save-prompt-on-win into the teaching moment), **or** just explain and point at the Recipe
   menu? **Recommend (a) offer Save directly in GUIs** (one-click common case; it *is* the §4.5 prompt);
   CLI/TUI print the text + the `save` hint.
3. **Wording home:** one shared **core/presenter helper per language** (recommended — thin UIs, matches
   `format_move_tally`), or each UI composes its own? **Recommend the core helper.**
4. **Spec change:** update `feature-spec.md` §4.9/§3.5/§4.5 to make the win celebration + recipe teaching
   **explicit and mandatory** (and add a compliance-checklist row 20), as part of the Python task?
   **Recommend yes** (Python-first, since it's the oracle).

## Related

- `tasks/reference/ui-design-principles.md`, `tasks/reference/feature-spec.md` — the authorities above.
- Precedent for the fan-out shape (one shared core string → every UI): the move-tally /
  learning-flow fan-outs, archived under `tasks/archive/2026/11/01/` and `tasks/archive/2026/10/26/`.
