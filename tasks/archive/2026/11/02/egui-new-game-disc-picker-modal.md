# egui — a "New Game" modal disc picker (mobile-friendly), replacing the inline DragValue

**Status:** DONE 2026-11-02 (William Emerison Six <billsix@gmail.com>) — implemented, committed, archived.
**Priority:** 5 **Difficulty:** 3
**Created:** 2026-11-02, from a mobile-web usability report: selecting the disc count by dragging is
awkward on touch.

## What this did

The egui/eframe GUI (`rust/hanoi-egui/src/main.rs`) used to pick the disc count with an inline
`egui::DragValue` ("Discs:") in the **Game** menu beside a "New Game" button. On mobile web a
`DragValue` is awkward — it needs a drag gesture (or a double-tap that pops the on-screen keyboard).
It was also the **odd one out**: the Python oracle's New Game opens a modal "How many discs?"
prompt (`hanoigui.py` `_on_new_game_prompt`, a `wx.NumberEntryDialog`), and the C++/wx GUIs use
discrete New-Game-1–10 items (`cpp/CLAUDE.md`).

Now **"New Game…"** in the Game menu opens a centered **"New Game"** window with a 5×2 grid of
tappable `1..=MAX_DISKS` buttons ("1 disc" / "N discs"); the current game size is highlighted, a tap
both picks and starts, and there is a Cancel (plus the window's close button). "New Game (Same
Size)" is unchanged. This fixes the touch UX and restores parity with the oracle's modal flow.

## What was built (all in `rust/hanoi-egui/src/main.rs`)

- Removed the `disc_count` field (struct, init, and its stale `new_game` assignment) and the inline
  `DragValue` + disc-reading "New Game" button.
- Added an `open_disc_picker: bool` flag; the Game menu's "New Game…" button sets it.
- Added the "New Game" picker as an `egui::Window` (the same pattern as the app's other dialogs —
  How-to-Play, "You solved it!", "Save solution?"), an `egui::Grid` of `selectable_label` buttons with
  the current size passed as the `selected` arg for the highlight; a click calls `request_new_game`.
- The feature is unchanged (New Game, 1..10), so no `feature-spec.md` or `CLAUDE.md` change — this is
  presentation only.

## Why a modal picker (and not the alternatives)

Mirroring the oracle's "How many discs?" modal was the maintainer's call, and it is also the best
touch UX. Alternatives weighed and rejected:

- **`+`/`−` stepper** — familiar, but up to 9 taps to reach the extremes and needs a separate Start.
- **`ComboBox` dropdown** — compact, but a dropdown inside a window is fiddly on mobile (3 taps).
- **A "New Game ▸" submenu of 1–10** (no modal) — simplest and also touch-friendly, but it doesn't
  match the oracle's modal flow and leaves the picker in a cramped menu. The chosen grid gives big
  tap targets and pick-and-start in one tap, and let the `disc_count` field be deleted.

## Durable notes (why the code looks the way it does)

- **egui 0.29 has no modal type.** egui/eframe is pinned `=0.29.1`; `egui::Modal` (a true
  input-blocking modal) only landed in egui 0.30. So the picker is an `egui::Window`, like every other
  "dialog" in this app. If egui is ever bumped past 0.30, convert all of these windows to `egui::Modal`
  as one batch.
- **The two-modal sequencing hazard.** A New Game over a hand-won, unsaved solution must still offer
  the save-before-discard prompt (`request_new_game` → `pending_new_game` → the "Save solution?"
  window). To avoid the two windows sharing a frame (the collision that bit the wx GUI — see
  `tasks/reference/win-celebration-and-recipe-discovery-ux.md`), the picker sets its flag false
  *before* calling `request_new_game`, and the save block is guarded by
  `pending_new_game.filter(|_| !picker_was_open)`, which defers it one frame.

## Verification

Gates ran 2026-11-02 under nested podman against the cached image (the compile invoked directly, not
via `make … : image`, to avoid the nested rebuild): egui `cargo check --all-targets` clean and
`cargo fmt --check` clean. The wxWidgets `--workspace` `make check`/`test` were not run — the change
is confined to the `hanoi-egui` separate workspace, which `--workspace` does not reach (`make
check-egui` is its gate). **Open follow-up (recommended, needs a display):** a visual check of the
picker on a narrow viewport — `cd rust && make egui` (native) or `make egui-web` + `make egui-serve`.

## Related

- `python/src/hanoigame/hanoigui.py` (`_on_new_game_prompt`) — the oracle's New Game modal this mirrors.
- `tasks/reference/win-celebration-and-recipe-discovery-ux.md` — the two-modal collision history.
- `tasks/reference/ui-design-principles.md` — the three-tier flow (New Game is a Tier-1 action).
- `tasks/reference/feature-spec.md` — the New Game feature + 1..10 range (the mandated part; the modal
  is presentation).
