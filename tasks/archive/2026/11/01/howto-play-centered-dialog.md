# Make "How to Play" a centered modal dialog in the wx GUIs + fix the ImGui one

**Status:** DONE — merged + on-display-verified by the maintainer (2026-11-01). The wx trio (wxPython
oracle + C++ wx + Rust wxDragon) now shows How-to-Play as a centered modal dialog (built in
`*_show_howto_dialog`, Centre'd + ShowModal, "don't show again" pref persisted, shown on first run +
from Help; the inline panel + View toggle are gone), and the C++ ImGui popup is centered on the
viewport with a ~520px width. egui/Tauri were already centered (unchanged). `ui-design-principles.md`
ruling 4 records the centered-dialog decision.
**Priority:** 4 **Difficulty:** 3 (small per UI; four files across two languages + one geometry fix)
**Created:** 2026-11-01 (William Emerison Six <billsix@gmail.com>, from an on-display review of the
graphical front-ends after the learning-flow + drag-drop fan-outs).

## BLUF

The first-run "How to Play" onboarding should appear as a **centered modal dialog in the middle of the
window** in every GUI — the style the **Tauri** front-end already uses (an HTML `<dialog>` opened with
`showModal()`) and that **egui** already approximates (a centered `egui::Window`). Two front-end
families are off that mark and this task brings them in line:

1. **The wx trio** (wxPython oracle + C++ wxWidgets + Rust wxDragon) currently shows How-to-Play as an
   **inline panel pinned to the top of the window**, not a dialog. Convert each to a **centered dialog**
   shown once on first run and reopenable from Help → How to Play (keeping the legal/illegal diagram and
   the "don't show again" preference).
2. **The C++ ImGui** How-to-Play is already a modal popup but it is **not centered and too narrow** —
   give it a sensible fixed width and center it on the viewport.

Done = every GUI's How-to-Play opens centered in the middle of the window; the wx ones are real dialogs
(not an inline panel); on-display-verified. No change to the text content or to when it shows (first run
+ Help). Update `tasks/reference/ui-design-principles.md` ruling 4 (it currently says "first-run
dismissible **panel**"; the settled form for GUIs is a centered **dialog**).

## Context (read first)

- **The reference (good) implementations — mirror these:**
  - **Tauri** — `rust/tauri/frontend/index.html` `<dialog id="howto-dialog" class="howto">` +
    `rust/tauri/frontend/main.js` `dialog.showModal()` (first run + Help) + `style.css` `dialog.howto`
    (`max-width: 28rem`). The browser centers a `showModal()` dialog automatically. This is the target
    look: centered, middle of the screen, dimmed backdrop.
  - **egui** — `rust/hanoi-egui/src/main.rs` `update()`: an `egui::Window::new("How to Play")`
    `.anchor(egui::Align2::CENTER_CENTER, ...)` `.collapsible(false).resizable(false)`. Already centered;
    left as-is (the model for the ImGui fix below).
- **The wx inline panel to replace (the oracle + its two ports), all built the same way:**
  - **wxPython oracle** — `python/src/hanoigame/hanoigui.py` `_build_howto_panel()` returns a
    `wx.Panel` that `_build_ui` adds to the frame's top sizer (`frame_sizer.Add(self._howto_panel, …)`)
    and `.Show()`s on first run; `CONFIG_SHOW_HOWTO` (wx.Config) is the "don't show again" pref; the
    `_LegalMoveDiagram` panel is the ✓/✗ figure; Help → How to Play and View → How to play toggle it.
  - **C++ wx** — `cpp/hanoiwx.cpp` `build_howto_panel()` (+ `LegalMoveDiagram`, `show_howto`,
    `kConfigShowHowto`, the Help/View items), added to `frame_sizer`.
  - **Rust wxDragon** — `rust/hanoi-gui/src/main.rs` `howto_panel` (built inline, `draw_legal_diagram`,
    `show_howto`, `CONFIG_SHOW_HOWTO`, the Help/View items), added to `frame_sizer`.
- **The ImGui modal to widen+center:** `cpp/main.cpp` `draw_help_modal()` — `BeginPopupModal("How to
  Play", nullptr, ImGuiWindowFlags_AlwaysAutoResize)` with no position/size set, so it opens at a
  default spot and `AlwaysAutoResize` lets the wrapped text sprawl/narrow unpredictably.
- **No core change.** This is pure presentation. The content (goal + the one rule + the solve-small-
  relabel-replay method + the ✓/✗ diagram) and the trigger (auto once on first run, reopen from Help)
  stay exactly as they are.

## Plan (per UI)

1. **wxPython oracle (`hanoigui.py`)** — turn the How-to-Play panel into a dialog. Options, in order of
   preference: (a) build a small `wx.Dialog` holding the heading + `HOWTO_TEXT` + `_LegalMoveDiagram` +
   the "Don't show this again" checkbox + a "Got it" button, `Centre()` it, and `ShowModal()` (or
   non-modal `Show()` centered) on first run and from Help; OR (b) move the existing panel's widgets
   into that dialog. Drop the `frame_sizer` inline panel and the board-shifting layout it caused. Keep
   `CONFIG_SHOW_HOWTO`, the diagram, and the Help entry; the View → "How to play" toggle can open the
   dialog (or be dropped — a dialog doesn't need a show/hide toggle). This is the oracle, so do it first
   and mirror it into the two ports.
2. **C++ wx (`cpp/hanoiwx.cpp`)** — the same conversion: `build_howto_panel()` → a centered `wxDialog`
   (reuse `LegalMoveDiagram`), shown on first run + from Help; remove it from `frame_sizer`.
3. **Rust wxDragon (`rust/hanoi-gui/src/main.rs`)** — the same: build a `Dialog` (wxDragon `Dialog`,
   as used for the recipe/rebinding monospace dialogs), centered, with the diagram panel + checkbox +
   button; show on first run + from Help; remove the frame-sizer panel.
4. **C++ ImGui (`cpp/main.cpp` `draw_help_modal`)** — before `BeginPopupModal`, center and size it:
   `ImGui::SetNextWindowPos(ImGui::GetMainViewport()->GetCenter(), ImGuiCond_Appearing, ImVec2(.5f,.5f));`
   and `ImGui::SetNextWindowSize(ImVec2(~520, 0), ImGuiCond_Appearing);` (width fixed, height auto); drop
   `AlwaysAutoResize` so the width sticks (the wrapped text then fills the fixed width). Match egui's feel.
5. **Verify:** each subproject's gate (`make build`/`check`/`type-check` as applicable) + the
   maintainer's **on-display** check that each How-to-Play opens centered in the middle of the window.
6. **Doc:** update `ui-design-principles.md` ruling 4 — the GUI onboarding is a **centered dialog**
   (first-run + reopenable from Help), not an inline panel. (A terminal UI's first-run text is unchanged.)

## Open questions

1. **Modal vs non-modal for the wx dialog?** Tauri uses modal (`showModal`), egui uses a floating
   centered window (effectively non-modal). Recommend **modal** for the wx first-run dialog (matches
   Tauri; forces the "Got it"/"don't show again" choice once), but non-modal is fine if modal fights the
   first-run timing. Decide during implementation; note which in the doc.

## Related

- `tasks/reference/ui-design-principles.md` — ruling 4 (onboarding) is what this revises; rulings 1–7
  are the fan-out decisions this follows.
- `tasks/archive/2026/11/01/fan-out-ui-learning-flow.md` — where the inline How-to-Play panel was added
  (the onboarding refinement being restyled here).
- `tasks/reference/feature-spec.md` §3.5 (onboarding tier), §7 row 19.
