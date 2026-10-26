# Rust wx GUI: load the shared wx XRC instead of building the UI in code

**Status:** DONE 2026-10-26 (William Emerison Six <billsix@gmail.com>) — maintainer confirmed the wx
window on-display ("the rust wx one works"/"looks good"). The design fork was resolved: **Rust conforms
to the XRC** (Python layout unchanged); Rust's dropped extras tracked in
`tasks/rust-wx-extra-features-to-python.md`. Two on-display polish fixes followed and are included
(same session): the board rendering was brought in line with the Python wx (transparent + centred bold
label badges, gradient background, bottom-centred text mode), and the rebinding / recipe-show views now
use a monospace dialog so the columns align (they were in a proportional `MessageDialog`).
**Priority:** 7 **Difficulty:** 6

## What was done (2026-10-26)

- **`rust/hanoi-gui/hanoi.xrc`** — git-tracked symlink → `../../ui/hanoi.xrc` (the shared file;
  same mechanism as cpp/python). **`rust/Makefile`** mounts `ui/` at `/ui` (`UI_MOUNT`, read-only) so
  the symlink resolves in the self-contained container, consistent with cpp.
- **`rust/hanoi-gui/Cargo.toml`** — enabled wxdragon's `xrc` feature (not a default).
- **`rust/hanoi-gui/src/main.rs`** — rewritten to load the UI from the XRC:
  `XmlResource::get().load_from_string(include_str!("../hanoi.xrc"))` (bakes the bytes into the binary,
  so **no runtime file and no Dockerfile bake** — simpler than the `include_xrc!` compile-time-file
  plan); `MenuBar::from_xrc_name("main_menubar")` + `load_panel("HanoiPanel")`; children via
  `find_child_by_xrc_name` (`move_1_2`…, `recipe_list`/`recipe_save`/`recipe_apply`/`recipe_show`,
  `board_slot`). The solid-fill DC board is drawn into a sub-panel of the XRC `board_slot`. Menu ids
  are resolved by `get_xrc_id` (an if/else chain, since they aren't compile-time constants).
- **Conformed to the XRC** (the maintainer's fork decision): dropped the code-built menu bar, the
  "How to play" item (not in the XRC), and the flat 6-button row (now the XRC's 3-column layout). The
  board-style items are the XRC's **radio** items. The rebinding/show views stay `MessageDialog`s.
- **Gate (hanoi-rust, nested):** `cargo fmt --check` clean; `cargo check --workspace --all-targets`
  RC=0 (wxdragon-sys recompiled for the `xrc` feature; no full wxWidgets rebuild). **On-screen
  correctness is unverified by the agent — the maintainer's `make wx` is the last check.**
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

## Findings 2026-10-26 (read `rust/hanoi-gui/src/main.rs` + `ui/hanoi.xrc`) — a migration, not a swap

The original framing ("replace the programmatic construction with `include_xrc!`") understated the
work: the Rust GUI (765 lines) and the shared XRC (the Python layout) have **diverged**, so loading the
XRC — which then becomes the authority for BOTH languages — forces reconciliation decisions. Concretely:

- **Board model differs.** The XRC has **one `board_slot` `wxPanel`** (Python swaps a text/graphics
  *renderer* into that one slot — `_swap_renderer`). The Rust GUI has **two stacked widgets**
  (`board_graphics: Panel` + `board_text: TextCtrl`), shows one at a time, and paints the graphics with
  a wxDC `on_paint` handler. Adopting `board_slot` means re-architecting the Rust board: either draw
  both text and graphics into the single slot, or restructure the toggle.
- **Move buttons differ.** The XRC lays the six buttons out as **three from-peg columns**
  (`move_1_2`/`move_1_3` | `move_2_1`/`move_2_3` | `move_3_1`/`move_3_2`); Rust builds a **flat 6-button
  row** in order `(1,2),(1,3),(2,1),(2,3),(3,1),(3,2)`. The IDs become XRCIDs (`move_1_2`…), so the
  Rust event wiring must look buttons up by XRCID.
- **Menu differs.** XRC `main_menubar`: Game (`wxID_NEW`/`game_new_same`/`wxID_EXIT`), Relabel (6 normal
  items), View (`style_text`/`style_graphics` as **radio**), `wxID_ABOUT`. Rust adds a **"How to play"**
  item and uses **check** items for the board style. So either the XRC gains a how-to-play item (and
  Rust keeps it) or Rust drops it; radio-vs-check must be reconciled.
- **The board_slot has a fixed `<size>-1,280</size>`** and sits in a `wxStaticBoxSizer` labelled
  "Board"; Rust's board is proportion-3 in a plain sizer. Visual parity is a judgment only a human on
  screen can confirm.

**Implication — a design fork to settle first (new Open question 2):** because the shared XRC becomes
the single UI authority, the divergences above must be resolved in ONE direction. Recommended: **extend
the XRC to be the superset** (add a how-to-play menu item; keep the board as one `board_slot` and have
Rust paint into it; decide radio vs check once) so neither language loses a feature, then make BOTH
Python and Rust match it. That is a bigger change than "rewrite the Rust GUI" — it touches Python too.

**Recommended mode:** do this **on-display, iteratively** (`cd rust && make wx`, watch the window,
adjust) — a blind autonomous rewrite can't verify layout/board/menu parity and risks a large broken
`main.rs`. Also prefer **`include_str!(crate-relative symlink) + XmlResource::load_from_string`** over
`include_xrc!`: it bakes the XRC bytes into the binary at compile time (no runtime file, so **no
Dockerfile bake needed**) and looks widgets up by XRCID like the Python/C++ code already does — only
the compile-time symlink-resolution (needs `ui/` mounted during the runtime `cargo build`) remains.

## Sharing the single `hanoi.xrc` — DECIDED: hoist to `ui/` + git-tracked symlinks

**Mechanism (maintainer-decided 2026-10-25; the same mechanism the C++ task
`tasks/archive/2026/10/25/cpp-add-wx-frontend-and-recipe-view-parity.md` uses, kept consistent):**

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
2. **The divergence fork — RESOLVED (maintainer, 2026-10-26): Rust conforms to the XRC** (the Python
   wx layout is the authority and stays as-is). Rust lost its "How to play" item and flat button row;
   the board is now one `board_slot`; style items are the XRC's radio. Whether Rust's extras (chiefly
   the "How to play" dialog) should instead be added to the Python oracle — and then fanned out to all
   UIs — is tracked separately in `tasks/rust-wx-extra-features-to-python.md`.

## Related

- Canonical UI: `python/src/hanoigame/hanoi.xrc` + `python/src/hanoigame/hanoigui.py`.
- runClaudeInContainer `tasks/reference/rust-gui-tui-and-ecosystem.md`; `tasks/reference/per-language-subproject-layout.md`
  (the self-contained-subproject model this has to work within).
