# C++ subproject: add a wxWidgets `make wx` front-end (shared XRC) + bring the ImGui GUI to recipe parity

**Status:** COMPLETE (2026-10-25) — both parts shipped and **confirmed on-display by the maintainer**
("the cpp wx looks right", "looks good on screen"). The `cpp/` subproject now has two spec-conformant
GUIs (Dear ImGui native+wasm, and a wxWidgets `make wx`) plus the shared-XRC `ui/` hoist. Conforms to
`tasks/reference/feature-spec.md`. Archive after the work commit.
**Priority:** 5 **Difficulty:** 6
**Created:** 2026-10-25 (William Emerison Six <billsix@gmail.com>). Requested: "the hanoi CPP one needs a
few updates. It needs a make wx target, using wxwidgets, using a shared xrc file from the python code.
also, for the IMGUI version, it doesn't have feature parity to the python one … being able to view
recipes, and upon invoking a recipe, show the recipe and the rebindings, and the final move set on the
global labels for the pegs."

## BLUF

Closed two parity gaps in the C++ subproject (`cpp/`, github.com/billsix/towersofhanoi):

- **Part A — a wxWidgets `make wx` front-end** (C++ wxWidgets/wxGTK) built from the **shared `hanoi.xrc`**
  the Python GUI uses, so the wx UI is defined once across languages and can't drift. The C++ sibling of
  `tasks/rust-gui-use-shared-xrc.md`.
- **Part B — ImGui/wasm recipe-view parity.** The GUI now shows, on invoking a recipe, the Python
  **three-panel view** (the recipe's moves | the **rebinding** recipe-label→physical-peg | the **rebound
  moves on the physical pegs**), plus the rest of the feature-spec gaps the audit found.

Python stays the behaviour oracle for both.

## Context

- **Canonical oracle (Python):** `python/src/hanoigame/recipe.py` (`rebinding` / `rebound_moves` /
  `format_rebinding_table` — the last is "the text-frontend equivalent of the GUI's three-panel rebinding
  view"); `hanoigui.py` (the wx GUI + `GraphicsBoardRenderer` in `board_renderers.py`, the board look to
  match); `hanoi.xrc` (the single wx UI layout). Rebinding-display rationale (the teaching moment):
  `tasks/archive/2026/09/14/record-recipe-bindings-and-show-rebinding.md`.
- **Split/parity rule:** each language is a self-contained subproject (`cpp/CLAUDE.md`,
  `tasks/reference/per-language-subproject-layout.md`); Python is the behaviour oracle, never removed;
  front-ends stay thin (logic in `cpp/src/`).
- **Shared-XRC mechanism (same as the Rust task):** hoist to a repo-root `ui/` + git-tracked symlinks +
  a mounted `ui/` (Decision 1). C++ wxWidgets loads XRC at **runtime** (`wxXmlResource::Load`), so unlike
  Rust's compile-time `include_xrc!` there was no build-time path constraint.

## Decisions (maintainer, 2026-10-25)

1. **XRC sharing: hoist + git-tracked symlinks.** `hanoi.xrc` is the one true file at `ui/hanoi.xrc`;
   each subproject keeps a git-tracked relative symlink at its existing path
   (`cpp/hanoi.xrc → ../ui/hanoi.xrc`, `python/src/hanoigame/hanoi.xrc → ../../../ui/hanoi.xrc`), and each
   Makefile mounts `ui/` → `/ui` so the symlink resolves in-container. One file, no drift, no loader-path
   changes — the same mechanism as `tasks/rust-gui-use-shared-xrc.md`.
2. **wxGTK added to the cpp image**, flag-gated (`USE_WX`) so a lean `MINIMAL_IMAGE` build drops it.
3. **Full parity** with the Python wx GUI (incl. the three-panel recipe view) — the standard for every
   implementation.
4. **Invoke semantics: defined by the feature spec** (§4.8) — invoking a recipe **shows** the three-panel
   view **and applies** the moves to the board **and records** them.
5. **One doc** for Parts A and B (committed separately).
6. **Order:** engine primitives → Part B (ImGui) → Part A (wx), with the `ui/` hoist done once (shared
   with the Rust task).
7. **No XRC bake needed (resolved on the maintainer's confirmation):** these podman images are
   **development-only, never pushed to a registry**, so there is no mount-less pulled-image case; the
   `/ui` mount is the XRC delivery mechanism. (`cpp/Dockerfile` + `feature-spec.md` say so.)

## What was built & verified

**Engine primitives** (`cpp/src/recipe.hpp`): `rebound_moves` + `format_rebinding_table` ported from
`recipe.py` (the engine already had `rebinding()`); both GUIs consume them.

**ImGui/wasm GUI** (`cpp/main.cpp`) — all eight feature-spec §7 gaps closed: the **three-panel recipe
view** on invoke (recipe moves | rebinding label→peg | rebound physical moves, shown under a non-default
labelling — for Apply, View, and a single relabelled move); **view a recipe** without replaying; **Apply
records** the applied moves; the **recipe list** carries disk/move counts; **Save** gated on win with
overwrite reported, and its name field **prefilled `solve-<N>`** (feature-spec §4.5); the optimal
`2^N−1` and the **physical 1,2,3 reference row** when relabelled; a **Help** popup and explicit **Quit**.
The six move buttons are **always shown** (no jump); illegal ones render **grayed** (muted style colours)
yet stay clickable, so a click still pops the **distinct rejection reason** in a min-width dialog.

**wxWidgets `make wx`** (`cpp/hanoiwx.cpp`) — a `wxApp` that `wxXmlResource::Load`s the shared XRC and
drives `cpp/src/` directly (there is no C++ engine-dispatch layer), at parity with `hanoigui.py`: menubar
+ panel + move buttons + recipe list bound by XRCID (illegal move buttons natively disabled/grayed); the
board **custom-drawn with `wxGraphicsContext`** as a faithful port of the Python `GraphicsBoardRenderer`
(discs coloured **by size** from the 10-colour palette, width interpolated smallest=⅓-largest, rounded
with a drop shadow + vertical gradient; cylinder-gradient pegs; base bar; label badges + the physical
reference row). Save (post-win, overwrite reported, `solve-<N>` prefilled), Apply (records + a three-panel
`RebindingDialog` when relabelled), Show (`RecipeDialog`), the relabel menu with an active bullet, a
2-field status bar.

**Shared-XRC plumbing:** `git mv python/src/hanoigame/hanoi.xrc → ui/hanoi.xrc`; the two git-tracked
relative symlinks (mode 120000); `/ui` mount added to **both** `cpp/Makefile` and `python/Makefile`;
`USE_WX` ARG + `cpp/entrypoint/03-install-wx.sh` (wxGTK-devel + libSM/libICE) dispatched by the Dockerfile
(its own group script, matching the repo's one-group-per-script convention); the `cpp/CMakeLists.txt` wx
target gated on `find_package(wxWidgets)` so a lean image still configures the ImGui target.

**Verification:** native ImGui and the wx app both **build + link clean** nested (pre- and
post-`clang-format`); the Python GUI still builds and its loader resolves the symlink via the `/ui` mount;
the wasm target built clean at implementation time (the later ImGui refinements — the `solve-<N>` prefill
and the grayed buttons — are native-verified and are trivial, Emscripten-identical changes, so the cached
no-emsdk image did not re-run them). **The maintainer confirmed the native + wx GUIs on-display** (discs,
prefill, grayed buttons, the widened error dialog).

**Judgment calls:** (a) wxGTK is its own `03-install-wx.sh` group script (not inlined), per convention;
(b) illegal move buttons — ImGui shows them grayed-but-clickable (so the distinct rejection reason can
still teach), wx disables them natively like Python — both spec-conformant; (c) the wx Text board style
is a simple peg/stack listing (the C++ engine doesn't port the Python ASCII-layout maths); Graphics is
the default.

## Related

- `tasks/rust-gui-use-shared-xrc.md` — the Rust sibling (identical shared-XRC mechanism).
- `tasks/archive/2026/10/25/port-to-cpp-imgui-native-and-wasm.md` — how the `cpp/` subproject + ImGui GUI
  were first built; `cpp/CLAUDE.md`; `tasks/reference/imgui-cpp-native-and-wasm.md`.
- `tasks/reference/feature-spec.md` — the parity authority (§4.5 save prefill, §4.8 recipe view, §7 checklist).
- `tasks/reference/per-language-subproject-layout.md`; the shared `rust-gui-tui-and-ecosystem.md`
  (runClaudeInContainer `tasks/reference/`) for the wx build deps.
- `tasks/archive/2026/09/14/record-recipe-bindings-and-show-rebinding.md` — the rebinding teaching moment.
- Oracle: `python/src/hanoigame/{recipe.py,presenter.py,hanoigui.py,board_renderers.py,hanoi.xrc}`.
