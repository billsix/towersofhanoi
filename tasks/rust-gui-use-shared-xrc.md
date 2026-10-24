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
  See `tasks/reference/rust-gui-tui-and-ecosystem.md` and
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
  **under the rust crate at build time**, at a path the macro references. This reshapes the sharing
  decision below — a *live* cross-subproject symlink dangles inside the isolated rust container, so a
  **build-time copy of the canonical XRC into the rust crate** (drift-guarded) is the robust mechanism.
- **Residual risk to check during the work:** that every widget type used in `hanoi.xrc` (authored for
  wxPython) is supported by wxDragon's XRC loader. If a widget isn't, adjust the XRC or fall back for
  that piece.

## Sharing the single `hanoi.xrc` — the real obstacle

`git` **does** track symlinks (`core.symlinks=true` on Linux), so a symlink is mechanically possible.
**But** the per-language subprojects are self-contained: `rust/`'s container mounts only `rust/` at
`/hanoi-rust`, and `python/`'s mounts only `python/` — so a symlink `rust/.../hanoi.xrc →
../../python/src/hanoigame/hanoi.xrc` resolves in a full checkout (and on the host) but **dangles inside
the isolated rust container** (the target escapes the mount). So a naive cross-subproject symlink breaks
the containerized build — which is why one was NOT created up front. Pick a sharing mechanism:

1. **Canonical-in-python + build-time copy (recommended — robust with the compile-time macro).** Keep
   `hanoi.xrc` canonical in `python/`; the rust build copies it into the rust crate before `include_xrc!`
   runs (a generated-from-canonical artifact), guarded by a check that the two bytes match so they can't
   drift. No cross-subproject symlink to dangle in the container; self-containment preserved. Because
   `include_xrc!` only needs the file present at build, a copy is exactly enough.
2. **Shared top-level location + mount** — move `hanoi.xrc` to a repo-level `ui/` dir; both `python/`
   and `rust/` reference it, and each subproject's Makefile mounts it into its container. One true copy,
   but costs a break in strict self-containment (an extra mount) + updating Python's loader path.
3. **Symlink** — `git` tracks symlinks, and a `rust/… → ../../python/…/hanoi.xrc` symlink resolves in a
   full checkout / on the host, so `include_xrc!` works there — but it **dangles inside the isolated
   rust container** (target escapes the `/hanoi-rust` mount), so it needs the python xrc mounted in too.
   Looser self-containment; option 1 is cleaner.

## Plan

1. Feasibility — DONE (wxDragon has `include_xrc!`). Confirm the exact macro signature/options against
   the current wxDragon crate version pinned in `rust/` (it moves fast), and that the widget types in
   `hanoi.xrc` load.
2. Pick + implement the sharing mechanism (open question 1; recommend the build-time copy).
3. Rewrite `rust/hanoi-gui/src/main.rs`: replace the programmatic UI with `include_xrc!(<xrc>, Ui)` and
   drive the generated typed struct (`ui.<widget>`), binding events to its fields; keep the wxDragon DC
   board renderer and the `Rc<RefCell<GuiState>>` pattern. Mirror the Python window structure so the two
   match.
4. Verify nested: `cd rust && make wx` builds + the GUI opens (maintainer confirms on the host); the
   window matches the Python one; the XRC-match drift check passes.

## Open questions

1. **Which sharing mechanism?** Recommend the **build-time copy** (option 1 above): canonical `hanoi.xrc`
   stays in `python/`, the rust build copies it in before `include_xrc!`, guarded by a bytes-match drift
   check. It's the robust fit for the compile-time macro and keeps both subprojects self-contained. The
   shared-`ui/`-dir + mount (option 2) is the alternative if you prefer one physical copy. Your call.

## Related

- Canonical UI: `python/src/hanoigame/hanoi.xrc` + `python/src/hanoigame/hanoigui.py`.
- `tasks/reference/rust-gui-tui-and-ecosystem.md`; `tasks/reference/per-language-subproject-layout.md`
  (the self-contained-subproject model this has to work within).
