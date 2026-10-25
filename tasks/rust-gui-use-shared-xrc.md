# Rust wx GUI: load the shared wx XRC instead of building the UI in code

**Status:** proposed — needs go-ahead (feasibility CONFIRMED 2026-10-24: wxDragon supports XRC via the
`include_xrc!` macro — so this is actionable).
**Priority:** 7 **Difficulty:** 5
**Created:** 2026-10-24 (William Emerison Six <billsix@gmail.com>). Requested alongside the C++ port:
"make a new task for the Rust one, to use that xrc file if it can, which will involve changing the rust
wx code, because that currently doesn't use xrc, it builds everything in code."

## BLUF

The Python wx GUI builds its window from a **wx XRC** file (`python/src/hanoigame/hanoi.xrc`, loaded as
package data). The Rust wxDragon GUI (`rust/hanoi-gui/`) instead builds the same UI **programmatically
in code**. This task: (1) determine whether **wxDragon exposes wxWidgets' `wxXmlResource` (XRC) loading**
— the "if it can" gate; (2) if it does, change the Rust GUI to **load the shared `hanoi.xrc`** so the
two front-ends share one UI definition and can't drift; (3) decide and implement **how the single
`hanoi.xrc` is shared** across the two self-contained subprojects. **Feasibility is confirmed**:
wxDragon loads XRC via its `include_xrc!` macro, so step (1) is done — proceed to the rewrite + sharing.

## Context (read first)

- **Python side:** `python/src/hanoigame/hanoigui.py` loads `hanoi.xrc` via
  `wx.xrc.XmlResource.Get().Load(...)` from `importlib.resources.files("hanoigame")/"hanoi.xrc"`, then
  binds widgets by XRCID. The XRC (≈15 KB) is the canonical UI definition.
- **Rust side:** `rust/hanoi-gui/src/main.rs` builds the window programmatically with wxDragon
  (`Rc<RefCell<GuiState>>` shared across `'static` closures; the DC-not-GraphicsContext drawing limit).
  See runClaudeInContainer `tasks/reference/rust-gui-tui-and-ecosystem.md` and
  `tasks/archive/2026/10/23/port-to-rust-wxdragon.md`.
- **Why share:** the Python package is the canonical source; all ports mirror it and must not drift. One
  shared XRC means the window layout is defined once, not reimplemented per language.

## Feasibility — CONFIRMED (2026-10-24, web research)

**wxDragon supports XRC** via an **`include_xrc!` macro**: you give it the XRC path and a struct name,
and it generates a **compile-time, type-safe UI struct** whose widgets are fields (e.g.
`ui.hello_button`). It wraps wxWidgets' XRC runtime (`wxXmlResource`), so the underlying two-step
load + child-lookup rules apply beneath the macro. wxDragon's docs recommend authoring the UI in a tool
like wxFormBuilder, but a hand-written / wxPython-authored XRC is standard XRC and should load. Sources:
wxDragon README/lib.rs listing (github.com/AllenDang/wxDragon, lib.rs/crates/wxdragon) and the wxWidgets
XRC overview (docs.wxwidgets.org/latest/overview_xrc.html).

- **Implication 1 — the original "built in code" was a choice, not a limitation.** So the rewrite is
  viable: replace the programmatic construction with `include_xrc!` + binding events to the typed
  widgets.
- **Implication 2 — `include_xrc!` is COMPILE-TIME** (like `include_str!`): the XRC file must be present
  **under the rust crate at build time**, at the path the macro references. The decided sharing mechanism
  (hoist + git-tracked symlink + a mounted `ui/`, below) satisfies this: with `ui/` mounted, the symlink
  at the crate's XRC path resolves to a real file at build time, so `include_xrc!` works with no copy.
- **Residual risk to check during the work:** that every widget type used in `hanoi.xrc` (authored for
  wxPython) is supported by wxDragon's XRC loader. If a widget isn't, adjust the XRC or fall back for
  that piece.

## Sharing the single `hanoi.xrc` — DECIDED: hoist to `ui/` + git-tracked symlinks

**Mechanism (maintainer-decided 2026-10-25; the same mechanism the C++ task
`cpp-add-wx-frontend-and-recipe-view-parity.md` uses, kept consistent):**

- **Hoist `hanoi.xrc` to a repo-root `ui/` dir** — the one true file (`ui/hanoi.xrc`).
- **A git-tracked relative symlink at each subproject's existing XRC path** points back to it:
  `python/src/hanoigame/hanoi.xrc → ../../../ui/hanoi.xrc`, `rust/hanoi-gui/<xrc-path> → …/ui/hanoi.xrc`
  (and `cpp/hanoi.xrc → ../ui/hanoi.xrc`). `git` tracks symlinks as mode `120000` (confirmed:
  `core.symlinks` is default/true on this Linux host). **Because each symlink sits at the path the loader
  already uses, nothing in code changes** (Python's `importlib.resources.files("hanoigame")/"hanoi.xrc"`
  still finds it; `include_xrc!` still references the crate path) — and there is **one physical file, so
  drift is impossible** (no bytes-match drift-guard needed).
- **In-container resolution:** each subproject's Makefile mounts the repo-root `ui/` at **`/ui`**
  (read-only). A subproject mounted at `/hanoi-<lang>` makes `..` resolve to `/`, so the relative symlink
  `../…/ui/hanoi.xrc` lands on `/ui/hanoi.xrc` inside the container. This is the one real cost — an extra
  mount per subproject (a small, deliberate break in strict self-containment).
- **Offline / baked image:** the subproject build context doesn't include `ui/`, so each Dockerfile must
  **bake the resolved `ui/hanoi.xrc`** into the image at the symlink's target path, so a pulled/offline
  image still has the UI definition (the "self-contained images" rule). Handle per Dockerfile.

This supersedes the earlier three-option sketch (canonical-in-python + build-time copy vs. shared `ui/`
mount vs. naive symlink): it is the shared-`ui/`-mount option refined with symlinks-back-to-the-old-path,
which removes that option's only costs (no loader-path change; no drift because it's one file).

## Plan

1. Feasibility — DONE (wxDragon has `include_xrc!`). Confirm the exact macro signature/options against
   the current wxDragon crate version pinned in `rust/` (it moves fast), and that the widget types in
   `hanoi.xrc` load.
2. Implement the decided sharing mechanism: hoist `hanoi.xrc` to `ui/`, create the git-tracked relative
   symlinks (python + rust at their existing XRC paths), mount `ui/` → `/ui` in each subproject's
   Makefile, and bake the resolved file per Dockerfile. (Do this hoist once, shared with the C++ task.)
3. Rewrite `rust/hanoi-gui/src/main.rs`: replace the programmatic UI with `include_xrc!(<xrc>, Ui)` and
   drive the generated typed struct (`ui.<widget>`), binding events to its fields; keep the wxDragon DC
   board renderer and the `Rc<RefCell<GuiState>>` pattern. Mirror the Python window structure so the two
   match.
4. Verify nested: `cd rust && make wx` builds + the GUI opens (maintainer confirms on the host); the
   window matches the Python one; the XRC-match drift check passes.

## Open questions

1. **Which sharing mechanism? — RESOLVED (maintainer, 2026-10-25): hoist to `ui/` + git-tracked
   symlinks** (see "Sharing the single `hanoi.xrc`" above). One physical file, no drift, no loader
   changes; each container mounts `ui/` so the symlink resolves. Done consistently with the C++ task.

## Related

- Canonical UI: `python/src/hanoigame/hanoi.xrc` + `python/src/hanoigame/hanoigui.py`.
- runClaudeInContainer `tasks/reference/rust-gui-tui-and-ecosystem.md`; `tasks/reference/per-language-subproject-layout.md`
  (the self-contained-subproject model this has to work within).
