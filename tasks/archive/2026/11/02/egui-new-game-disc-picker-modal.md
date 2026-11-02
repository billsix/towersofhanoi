# egui — a "New Game" modal disc picker (mobile-friendly), replacing the inline DragValue

**Status:** DONE 2026-11-02 (William Emerison Six <billsix@gmail.com>) — implemented and staged, not
committed (stage-only default). Ready to archive after the maintainer's work commit. Design settled +
both open questions resolved 2026-11-02 (Option 1 button grid, highlight the last-used count).
**Priority:** 5 **Difficulty:** 3
**Created:** 2026-11-02 (William Emerison Six <billsix@gmail.com>). From a mobile-web usability
report: selecting the disc count by dragging is awkward on touch.

## BLUF

The egui/eframe GUI (`rust/hanoi-egui/`) selects the disc count with an inline
`egui::DragValue` ("Discs:") sitting in the **Game** menu, next to a "New Game" button
(`src/main.rs:546-554`). On **mobile web** a `DragValue` is awkward: it needs a drag gesture (or a
double-tap that pops the on-screen keyboard). Two things point the same way: (a) it's poor for
touch, and (b) it **diverges from the Python oracle**, whose New Game opens a modal **"How many
discs?"** prompt (`python/src/hanoigame/hanoigui.py:526-542`, a `wx.NumberEntryDialog`). The fix the
maintainer wants: make egui's **"New Game" open a modal disc picker** (mirroring the oracle), with a
**tap-friendly** 1–10 selection inside; keep **"New Game (Same Size)"** promptless. "Done" = no
`DragValue`; New Game opens a modal; picking a number starts the game; pure tap targets; parity with
the oracle's flow; all Rust gates green.

## Context (read first)

- **Current egui code.** Game menu: `src/main.rs:545-560` — a `ui.horizontal` with `ui.label("Discs:")`
  + `egui::DragValue::new(&mut self.disc_count).range(1..=MAX_DISKS)` (line 548), then a "New Game"
  button that reads `self.disc_count` and calls `self.request_new_game(n)` (550-554), and "New Game
  (Same Size)" which reuses `self.game.num_disks` (555-559). The `disc_count` field is `main.rs:143`;
  `MAX_DISKS = 10` (`main.rs:25`).
- **The oracle's flow (what to mirror).** `hanoigui.py:526-542`: New Game → `wx.NumberEntryDialog`
  ("How many discs?", "Discs:", default = last count, range `1..=MAX_DISKS`) shown modal; on OK it runs
  `_maybe_offer_save_before_discard()` then `_new_game(n)`. "New Game (Same Size)" (`:547-551`) skips
  the prompt and reuses the last count.
- **egui's modal story at our pin.** egui/eframe is pinned **`=0.29.1`** (`Cargo.toml:23-24`).
  `egui::Modal` (a true input-blocking modal) landed in **egui 0.30**, so it is **not** available here.
  The app already emulates modals with `egui::Window`: How-to-Play (`main.rs:708`), "You solved it!"
  (`:734`), "Save solution?" (`:758`), each a `Window::new(...).open(&mut flag)`. The disc picker should
  follow that **same `egui::Window` + bool-flag pattern** (add e.g. `open_disc_picker: bool`), so no
  version bump and consistent with the app. (If egui is ever bumped past 0.30, switch these to
  `egui::Modal` as a batch.)
- **Save-before-discard sequencing (a real nuance — get it right).** New Game must still offer to save
  an unsaved solution first. In egui that is the existing `request_new_game(n)` → `pending_new_game =
  Some(n)` → the "Save solution?" window (`main.rs:208-212`, `756-779`). So the flow becomes **two
  sequential windows, never stacked**: tap New Game → *disc-picker* window → pick N → `request_new_game(N)`
  → (if an unsaved solution exists) the *Save-solution?* window → `new_game(N)`. Both are flag-gated, so
  they render in sequence naturally — but verify the picker closes before the save prompt shows (don't
  let both be open at once, the same two-modal collision that bit the wx GUI; see
  `tasks/reference/win-celebration-and-recipe-discovery-ux.md`).
- **Parity note (scope).** The C++/wx GUIs already use discrete "New Game 1–10" menu items / a number
  prompt (`cpp/CLAUDE.md`), so **egui is the outlier** and this change aligns it. Scope here is **egui
  only** (the mobile-web target). The Tauri HTML frontend has its own control; not in scope unless the
  maintainer asks.

## Options (the picker UI inside the modal)

1. **(recommended) Modal + a 1–10 button grid, tap-to-start.** A `Window` ("New Game") with the ten
   counts as buttons in a small grid (e.g. 5×2), each a comfortable tap target; **tapping a number is
   pick-and-start** (one tap), plus a **Cancel**. Best touch UX — open New Game (1 tap), pick+start
   (1 tap) — mirrors the oracle's "ask how many" intent, and lets the `disc_count` field be **deleted**
   (a small simplification). Default/last count can be visually marked (a highlighted/`selected` button).
2. **Modal + a `+`/`−` stepper around a big number + Start/Cancel.** Two big tap targets; familiar; but
   up to 9 taps to reach the extremes, and needs a separate Start tap.
3. **Modal + a `ComboBox` (dropdown) of 1–10 + Start/Cancel.** Compact, but a dropdown inside a window is
   fiddly on mobile and costs three taps (open, pick, Start).
4. **(not a modal) A "New Game ▸" submenu of 1–10 in the Game menu.** The earlier idea: simpler, no
   window, also touch-friendly (nested `menu_button` is already used for recipes, `main.rs:590`). But it
   does **not** match the oracle's modal flow the maintainer now prefers, and keeps the picker in a
   cramped menu. Kept here as the fallback if a modal feels heavy.

## Decision (William Emerison Six <billsix@gmail.com>, 2026-11-02)

**Option 1**, with the last-used count highlighted. A "New Game" modal (`egui::Window` + an
`open_disc_picker` flag) shows a 1–10 button grid; tapping a count both picks and starts (Cancel to back
out); the button for the last-used count is visually marked (`selected`); **"New Game (Same Size)"**
stays promptless. Rationale: matches the Python oracle's "How many discs?" modal flow (parity); best
mobile UX (big tap targets, no drag, pick+start in one tap); removes the inline `DragValue` and the
`disc_count` field (simplification); reuses the app's existing modal-window pattern (no egui bump).

## Plan

1. **Add state:** an `open_disc_picker: bool` field (init `false`, next to `open_help` / `pending_new_game`
   at `main.rs:105-150`), and keep the last-used count — reuse `self.game.num_disks` as the highlight
   source (so the `disc_count` field at `main.rs:143` can be removed, and its two reads at `:548,551`
   with it).
2. **Game menu (`main.rs:545-560`):** delete the `ui.horizontal`/`DragValue` block and the disc-reading
   "New Game" button; replace with a single **"New Game…"** button that sets `self.open_disc_picker =
   true` and closes the menu. Leave "New Game (Same Size)" (`:555-559`) unchanged.
3. **The picker window:** mirror the existing `Window::new(...).open(&mut flag)` dialogs (How-to-Play
   `:708`, "Save solution?" `:758`). A `Window::new("New Game")`, not resizable, collapsible off,
   anchored centre; inside, a grid (e.g. `egui::Grid` 5×2) of buttons `1..=MAX_DISKS`. Use
   `ui.selectable_label(n == self.game.num_disks, text)` (or a `Button` with `.selected(...)`) so the
   last-used count reads as highlighted. On a click: set `self.open_disc_picker = false`, then
   `self.request_new_game(n)`.
4. **Sequencing (the one hazard):** `request_new_game(n)` may raise the "Save solution?" window via
   `pending_new_game` (`:208-212, 756-779`). Because the picker sets its own flag false *before* calling
   `request_new_game`, the picker is gone before the save prompt can show — verify the two are never open
   simultaneously (the two-modal collision; see the win-celebration UX doc). Cancel just clears
   `open_disc_picker`.
5. **Gates:** `cd rust && make check-egui` (its own workspace — `make check`/`--workspace` doesn't reach
   it) + `make check` + `make test` + `make format`. Then display-verify: run `make egui` (native) and,
   ideally, `make egui-web` + `egui-serve` and tap through on a narrow viewport.
6. Update `rust/CLAUDE.md`'s egui description if it mentions the disc control; the feature is unchanged
   (New Game 1..10) so `feature-spec.md` needs no change — this is presentation only.

## Done — what was built (2026-11-02)

All in `rust/hanoi-egui/src/main.rs`:
- Removed the `disc_count` field (struct + init + the stale `new_game` assignment) and the inline
  `egui::DragValue` + "New Game" button from the Game menu.
- Added an `open_disc_picker: bool` flag; the Game menu now has a single **"New Game…"** button that
  sets it (plus the unchanged "New Game (Same Size)").
- Added a **"New Game"** `egui::Window` (same pattern as How-to-Play / Save-solution — egui 0.29 has no
  `egui::Modal`): a 5×2 `egui::Grid` of `selectable_label` buttons `1..=MAX_DISKS` ("1 disc" / "N
  discs"), with the current game size highlighted via the `selected` arg; a tap both picks and starts
  (`request_new_game`), plus a **Cancel** (and the window's close button).
- **Sequencing:** the picker sets its flag false *before* calling `request_new_game`, and the
  save-before-discard block is guarded by `pending_new_game.filter(|_| !picker_was_open)`, so the picker
  and the "Save solution?" window never render in the same frame (no two-modal overlap).
- No `feature-spec.md`/`CLAUDE.md` change — presentation only; the New Game 1..10 feature is unchanged.

**Gates (2026-11-02, nested podman, cached image — ran the compile directly, not `make … : image`):**
egui `cargo check --all-targets` clean; `cargo fmt --check` clean (after one wrap fix). Not run: the
wxWidgets `--workspace` `make check`/`test` (my change is only in the separate `hanoi-egui` workspace,
which `--workspace` doesn't reach). **Not yet done:** a display verify (`make egui` native / `make
egui-web` + `egui-serve` on a narrow viewport) — recommended, needs a display.

## Open questions

*(Both resolved 2026-11-02 — see Decision.)*

1. ~~Picker layout~~ — **Option 1** (1–10 button grid, tap-to-start).
2. ~~Default selection~~ — **highlight the last-used count** in the grid.

## Related

- `python/src/hanoigame/hanoigui.py:526-551` — the oracle's New Game modal flow this mirrors.
- `rust/hanoi-egui/src/main.rs:545-560`, `208-212`, `756-779` — the egui code to change and the
  save-before-discard windows to sequence with.
- `tasks/reference/ui-design-principles.md` — the three-tier flow; New Game is a Tier-1 action.
- `tasks/reference/win-celebration-and-recipe-discovery-ux.md` — the two-modal collision history (why
  the picker and the save prompt must sequence, not stack).
- `tasks/reference/feature-spec.md` — the UI-independent feature definitions (the modal is presentation;
  the New Game feature + 1..10 range is the mandated part).
