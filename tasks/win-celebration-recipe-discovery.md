# Win celebration + recipe discovery — realize the "teaching hinge" on winning (umbrella)

**Status:** implemented 2026-11-01 across all three languages (on branch `win-celebration-recipe-discovery`)
— Python (oracle, 3 front-ends + spec row 20), Rust (crate + 5 front-ends), C++ (core + 2 GUIs). Each
language's headless gate is green (see the child tasks). **Pending:** the maintainer's display-verify of
the GUIs (and the C++ `make webassembly` build); each child archives on its own confirmation, the
umbrella when the last one lands.
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

**When it shows (decided 2026-11-01, William Emerison Six <billsix@gmail.com>):**
- **Every win** = congrats + result + the **Save-as-recipe affordance** (prefilled `solve-<N>`). This
  realizes §4.5's "save prompt on winning" on *every* win, so any winning solve (not just the first) can
  be saved.
- **First win of the session additionally** = the **recipe teaching explanation** (part 2 above) — a
  one-time teaching moment (a GUI **modal** like "How to play"; a printed block in CLI/TUI) that explains
  what recipes are and the "solve small, relabel, replay" idea. **Later wins drop only the teaching
  paragraph** (don't re-teach — HIG), but keep the congrats + the save offer.

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

## Open questions — resolved 2026-11-01 (William Emerison Six <billsix@gmail.com>)

1. ~~Trigger?~~ **The teaching explanation is first-win-only** (don't over-modal — HIG). The congrats +
   save offer, however, shows on **every** win (see Q2). So: first win = teaching modal; every win =
   congrats + save affordance.
2. ~~Offer Save directly, and on which wins?~~ **Yes — offer Save directly in the popup** (a "Save as
   recipe" button prefilled `solve-<N>`), **and on every win**, not just the first. This merges §4.5's
   save-prompt-on-win into the moment. CLI/TUI print the text + the `save <name>` hint each win.
3. ~~Wording home?~~ **Shared core/presenter helper per language** (thin UIs; matches `format_move_tally`).
4. ~~Spec change?~~ **Yes** — update `feature-spec.md` §4.9/§3.5/§4.5 and add compliance row 20, in the
   Python task (Python is the oracle).

## Related

- `tasks/reference/ui-design-principles.md`, `tasks/reference/feature-spec.md` — the authorities above.
- Precedent for the fan-out shape (one shared core string → every UI): the move-tally /
  learning-flow fan-outs, archived under `tasks/archive/2026/11/01/` and `tasks/archive/2026/10/26/`.
