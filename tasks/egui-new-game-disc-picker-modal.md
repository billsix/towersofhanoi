# egui — a "New Game" modal disc picker (mobile-friendly), replacing the inline DragValue

**Status:** proposed — needs go-ahead + a pick among the picker layouts (open question 1).
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

## Recommendation

**Option 1** — a "New Game" modal (`egui::Window` + an `open_disc_picker` flag) showing a 1–10 button
grid, where tapping a count both picks and starts (Cancel to back out), and **"New Game (Same Size)"**
stays promptless. Rationale: matches the Python oracle's "How many discs?" modal flow (parity); best
mobile UX (big tap targets, no drag, pick+start in one tap); removes the inline `DragValue` and the
`disc_count` field (simplification); reuses the app's existing modal-window pattern (no egui bump). The
one thing to implement carefully is the save-before-discard **sequencing** above.

## Open questions

1. **Picker layout** — Option 1 (1–10 button grid, recommended) / 2 (stepper) / 3 (combo) / 4 (menu
   submenu, no modal)? See Options above. Your call; I recommend 1.
2. **Default selection** — pre-select/highlight the last-used count in the grid (recommended), or no
   default (every start is an explicit pick)? Minor.

## Related

- `python/src/hanoigame/hanoigui.py:526-551` — the oracle's New Game modal flow this mirrors.
- `rust/hanoi-egui/src/main.rs:545-560`, `208-212`, `756-779` — the egui code to change and the
  save-before-discard windows to sequence with.
- `tasks/reference/ui-design-principles.md` — the three-tier flow; New Game is a Tier-1 action.
- `tasks/reference/win-celebration-and-recipe-discovery-ux.md` — the two-modal collision history (why
  the picker and the save prompt must sequence, not stack).
- `tasks/reference/feature-spec.md` — the UI-independent feature definitions (the modal is presentation;
  the New Game feature + 1..10 range is the mandated part).
