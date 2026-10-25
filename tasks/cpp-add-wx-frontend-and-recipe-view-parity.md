# C++ subproject: add a wxWidgets `make wx` front-end (shared XRC) + bring the ImGui GUI to recipe parity

**Status:** ready — decisions made (2026-10-25, see Decisions). Part A (wx + shared XRC) can start now;
Part B (recipe view) conforms to the feature spec `tasks/archive/2026/10/25/program-feature-spec-and-compliance.md`, so it
follows that spec landing.
**Priority:** 5 **Difficulty:** 6
**Created:** 2026-10-25 (William Emerison Six <billsix@gmail.com>). Requested: "the hanoi CPP one needs a
few updates. It needs a make wx target, using wxwidgets, using a shared xrc file from the python code.
also, for the IMGUI version, it doesn't have feature parity to the python one … being able to view
recipes, and upon invoking a recipe, show the recipe and the rebindings, and the final move set on the
global labels for the pegs."

## BLUF

The C++ subproject (`cpp/`, github.com/billsix/towersofhanoi) ships one GUI (Dear ImGui, native + wasm)
and is **not yet at parity with the canonical Python** on two counts. This task closes both:

- **Part A — a wxWidgets `make wx` front-end** (C++ wxWidgets / wxGTK), building its window from the
  **shared `hanoi.xrc`** that the Python GUI already uses, so the wx UI is defined once across languages
  and can't drift. This is the C++ sibling of `tasks/rust-gui-use-shared-xrc.md` (Rust/wxDragon).
- **Part B — ImGui recipe-view parity.** The Python GUI, on invoking a recipe, shows a **three-panel
  view**: the recipe's moves (its own labels), the **rebinding** (this recipe's labels → physical pegs),
  and the **rebound move set on the global/physical peg labels**. The C++ ImGui GUI today only *replays*
  a recipe (one-line status) plus a *static* current-labelling rebinding panel — so it must gain the
  recipe view + the on-invoke three-panel display.

"Done" = (A) `cd cpp && make wx` opens a wxWidgets window driven by the shared `hanoi.xrc`, at parity
with the Python wx GUI, with the XRC shared (not duplicated-by-hand) and drift-guarded; (B) the ImGui GUI
lets you view a saved recipe and, on invoking it, shows the recipe + rebinding + rebound physical moves,
matching the Python three-panel view. Python stays the behaviour oracle for both.

## Context (read first)

- **Canonical oracle (Python):**
  - Recipe engine: `python/src/hanoigame/recipe.py` — `Recipe`/`Recorder`/`RecipeRegistry`, and the
    rebinding API: **`rebinding(labelling)`** (recipe's local labels → physical pegs),
    **`rebound_moves(moves, labelling)`** (the recipe's moves translated to physical pegs), and
    **`format_rebinding_table(...)`** whose docstring calls itself *"the text-frontend equivalent of the
    GUI's three-panel rebinding view: `<left_header> | Rebinding (label -> peg) | Rebound (physical
    pegs)`"* — that three-panel layout is the Part-B target.
  - wx GUI: `python/src/hanoigame/hanoigui.py` — loads `hanoi.xrc` via
    `wx.xrc.XmlResource.Get().Load(...)` from package data, binds widgets by XRCID, custom-draws the
    board, and presents the recipe view + three-panel rebinding. This is the Part-A oracle.
  - Shared UI definition: **`python/src/hanoigame/hanoi.xrc`** (~15 KB) — the single wx UI layout.
  - Design rationale for showing the rebinding (the teaching moment): the archived
    `tasks/archive/2026/09/14/record-recipe-bindings-and-show-rebinding.md`.
- **Current C++ state:**
  - Engine `cpp/src/recipe.hpp` **already has** `rebinding(Labelling)` and per-move label→physical
    translation — so Part B is mostly a GUI addition (iterate the recipe's moves through the existing
    translation; add a batch `rebound_moves` helper if cleaner).
  - GUI `cpp/main.cpp`: the Recipe menu does Save / Reset / **Replay ▸ <name>** (replay applies the moves
    and sets a one-line status), and there is a *static* panel "Rebinding (a recipe's labels → physical
    pegs …)" for the **current labelling** — not tied to invoking a specific recipe, and with no
    recipe-moves or rebound-moves columns. That is the parity gap.
  - The cpp image (`cpp/Dockerfile`, `cpp/entrypoint/01-install-cpp-base.sh`) installs **SDL2 + mesa/GL
    only — no wxWidgets/GTK**. Part A needs `wxGTK-devel` (+ `libSM/libICE-devel`) added (see the Rust
    wx build-dep notes in the shared `rust-gui-tui-and-ecosystem.md`, runClaudeInContainer
    `tasks/reference/`).
- **The split/parity rule:** each language is a self-contained subproject (`cpp/CLAUDE.md`,
  `tasks/reference/per-language-subproject-layout.md`); the Python package is the behaviour oracle and
  is never removed to satisfy a port. New front-ends stay thin — logic lives in `cpp/src/`.
- **Prior art, same mechanism:** `tasks/rust-gui-use-shared-xrc.md` uses the identical shared-XRC
  mechanism — hoist to `ui/` + git-tracked symlinks + a mounted `ui/` (see Decision 1). C++ has it
  easier: wxWidgets loads XRC at **RUNTIME** (`wxXmlResource::Load`), unlike wxDragon's compile-time
  `include_xrc!`, so there is no build-time path constraint at all.

## Part A — wxWidgets `make wx` front-end from the shared XRC

### Plan
1. **Add wxWidgets to the cpp image** — `wxGTK-devel` (+ `libSM-devel`/`libICE-devel`) in
   `01-install-cpp-base.sh`, under a flag so a lean image can drop it (`USE_X_WINDOWS`-style, per the
   `MINIMAL_IMAGE` idiom). Keep SDL2/GL for the ImGui target.
2. **Share `hanoi.xrc` (hoist + symlink; see Decision 1).** Hoist to `ui/hanoi.xrc`; add the git-tracked
   symlink `cpp/hanoi.xrc → ../ui/hanoi.xrc`; mount `ui/` → `/ui` in `cpp/Makefile` so it resolves inside
   the `/hanoi-cpp` container; bake the resolved file in `cpp/Dockerfile` for offline images. wx loads
   XRC at **runtime** (`wxXmlResource::Load`), so a resolved symlink/mounted file is all it needs — no
   compile-time constraint. Do the hoist once (shared with the python + rust symlinks).
3. **`cpp/hanoi-wx` front-end** — a thin wxWidgets `wxApp`/`wxFrame` that `wxXmlResource::Load`s the
   shared XRC, binds widgets by `XRCID`, custom-draws the board (wxDC — same limit the Rust GUI hit), and
   drives `cpp/src/` (model/presenter/recipe) exactly as the ImGui and Python front-ends do. Parity with
   `hanoigui.py`: menubar (disk count / relabel / recipe), board coloured by label, moves in current
   labels, the recipe view (shared with Part B's model).
4. **`make wx` target** — build + run under the existing X11/Wayland passthrough (the ImGui `make gui`
   target is the template), `cpp/CMakeLists.txt` building the wx target alongside the ImGui ones.
5. **Verify** — `make wx` opens on a display; offline/self-contained rebuild still holds; `make format`
   clean; the XRC drift guard passes.

## Part B — ImGui recipe view + on-invoke three-panel display

### Plan
1. **Recipe view** — in `cpp/main.cpp`, let the user **select/view a saved recipe** (not only replay it),
   showing its stored moves (default-label space).
2. **On invoke, the three-panel display** — matching Python's `format_rebinding_table` / the GUI view:
   (a) the **recipe's moves** in its own labels; (b) the **rebinding** (recipe label → physical peg) for
   the current labelling, via the existing `hanoi::rebinding`; (c) the **rebound move set on the global
   (physical) peg labels**. Decide whether invoking still *applies* the moves to the board as today, or
   only shows the view, or both (open question 4).
3. **Engine** — reuse `cpp/src/recipe.hpp`'s `rebinding` + per-move translation; add a small batch
   `rebound_moves` helper if it makes the GUI code cleaner (keep it a faithful port of `recipe.py`).
4. **Verify** — native + wasm build/link; the view matches the Python oracle for a sample recipe under a
   non-default labelling; `make format` clean.

### Spec-compliance gaps (from the 2026-10-25 audit — `tasks/archive/2026/10/25/program-feature-spec-and-compliance.md`)

The audit against `tasks/reference/feature-spec.md` §7 found the ImGui GUI is missing more than the
three-panel view. Part B should close all of these (ranked, biggest first):
1. **Three-panel rebinding view on apply (row 13, biggest):** port `rebound_moves` + `format_rebinding_table`
   (the engine has only `rebinding()`), and render three panels on invoke — recipe moves | rebinding
   (label→peg) | rebound physical moves — shown only under a non-default labelling. Replace the current
   one-line status + static middle-only panel.
2. **Show a recipe without replaying (row 11):** the GUI can only replay; add a view of a recipe's moves
   (default-label space) with disk/move counts.
3. **Apply must record the applied moves (row 12):** `hanoi::apply` / its call site must feed the recorder
   (as Python's `_handle_apply` does), so a replayed solve is itself saveable.
4. **Recipe list with disk + move counts (row 10):** the Replay submenu shows names only.
5. **Distinct move-rejection reasons (row 4):** illegal moves are only disabled buttons; surface
   range/same-peg/empty/larger-on-smaller as a dialog (spec §6.2).
6. **Save gated on win + overwrite reporting (row 9):** gate the save affordance on the win, and report
   overwrite vs. new save.
7. **Show the optimal `2^N−1` (row 3)** and the **physical 1,2,3 reference row when relabelled (row 6)**.
8. **Help reference + an explicit in-app Quit (row 14).**

## Decisions (maintainer, 2026-10-25)

1. **XRC sharing (Q1): hoist + git-tracked symlinks.** Hoist `hanoi.xrc` to a repo-root `ui/` dir (the
   one true file); each subproject keeps a git-tracked relative symlink at its existing XRC path
   (`cpp/hanoi.xrc → ../ui/hanoi.xrc`; `python/src/hanoigame/hanoi.xrc → ../../../ui/hanoi.xrc`), and each
   Makefile mounts `ui/` → `/ui` so the symlink resolves in-container; bake the resolved file per
   Dockerfile for offline images. One file, no drift, no loader-path changes — the same mechanism as
   `tasks/rust-gui-use-shared-xrc.md`. (Supersedes the earlier build-time-copy answer.)
2. **Add wxGTK to the cpp image (Q2): YES** — add `wxGTK-devel` (+ `libSM/libICE-devel`), flag-gated so a
   lean image can drop it.
3. **Scope (Q3): FULL PARITY** — match the full Python wx GUI, including the three-panel recipe view.
   This is the standard for **every** implementation (Rust included), not just C++.
4. **Invoke semantics (Q4): deferred to the feature spec** — `tasks/archive/2026/10/25/program-feature-spec-and-compliance.md`
   defines (from the Python oracle) what invoking a recipe shows and whether it also applies to the board;
   this task conforms to that spec rather than guessing.
5. **Structure (Q5): one doc** — keep Parts A and B here; commit them separately.
6. **Order (approved 2026-10-25):** (i) port the shared C++ engine primitives `rebound_moves` +
   `format_rebinding_table` into `cpp/src/recipe.hpp` (both GUIs consume them); then (ii) **Part B** (the
   ImGui recipe view — smaller, unblocked, the gap the maintainer flagged); then (iii) **Part A** (the wx
   front-end — the bigger piece: wxGTK image dep + the `ui/` hoist + symlinks). The `ui/` hoist is done
   once and is shared with `rust-gui-use-shared-xrc.md`.

**This task is now spec-driven:** once `tasks/archive/2026/10/25/program-feature-spec-and-compliance.md` lands, Parts A and B
conform to the spec's recipe-view / rebinding definition (the parity authority), not to an ad-hoc reading
of the other GUIs.

## Open questions (resolved — see Decisions above)

1. **(Part A) XRC sharing mechanism** — adopt `rust-gui-use-shared-xrc.md`'s recommended **build-time
   copy of `python/src/hanoigame/hanoi.xrc` into `cpp/`, drift-guarded**? (Recommended; wx's runtime XRC
   load makes a copy sufficient, no compile-time path constraint.) Or a shared top-level `ui/` dir mounted
   into each subproject? See that task's three options.
2. **(Part A) adding wxGTK to the cpp image** — OK to add `wxGTK-devel` as a real runtime dep of the cpp
   subproject (it enlarges the full image; a `MINIMAL_IMAGE`/flag build would drop both wx and the Emscripten
   SDK)? The subproject would then carry two GUI toolkits (SDL2/GL for ImGui, GTK for wx).
3. **(Part A) scope of wx parity** — match the full Python wx GUI (incl. the recipe three-panel view, so
   Parts A and B share one recipe-view model), or a first cut that reaches the menubar + board + basic
   recipe replay and defers the three-panel view to a follow-up?
4. **(Part B) invoke semantics** — on invoking a recipe, should the ImGui GUI (a) only *show* the
   recipe + rebinding + rebound moves, (b) only *apply* the moves to the board as it does today, or (c)
   both (show the view and apply)? The Python GUI shows the view; confirm the desired interaction.
5. **(structure) one task or two** — Parts A and B are independent (a new front-end vs. an ImGui
   enhancement) and have independent commit boundaries; keep them in this one doc, or split B into its own
   task since it is much smaller and unblocked? (Recommend: keep one doc; commit A and B separately.)

## Related

- `tasks/rust-gui-use-shared-xrc.md` — the Rust sibling (shared-XRC analysis + the three sharing options).
- `tasks/archive/2026/10/25/port-to-cpp-imgui-native-and-wasm.md` — how the `cpp/` subproject + ImGui GUI
  were built; `cpp/CLAUDE.md` + `tasks/reference/imgui-cpp-native-and-wasm.md`.
- `tasks/reference/per-language-subproject-layout.md` — the subproject template; `rust/hanoi-gui/` as the
  wx-in-a-port precedent, and the shared `rust-gui-tui-and-ecosystem.md` (runClaudeInContainer
  `tasks/reference/`) for the wx build deps + the DC-not-GraphicsContext drawing limit.
- `tasks/archive/2026/09/14/record-recipe-bindings-and-show-rebinding.md` — why the rebinding is shown
  (the teaching moment behind Part B).
- Oracle: `python/src/hanoigame/{recipe.py,presenter.py,hanoigui.py,hanoi.xrc}`.
