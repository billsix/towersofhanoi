# Make the egui / ImGui / Tauri Game menu match the wx shape (New Game + Same Size)

**Status:** DONE + on-display-verified (maintainer, 2026-11-01: "menus look good"). Merged to master
(work commit `b727588`). Presentation-only; no core/logic change. Decided shape (maintainer,
2026-11-01): **every GUI's Game menu matches the wx trio** — a disc-count picker to start a **New
Game**, plus **New Game (Same Size)** that restarts at the current count. wx is the reference
(unchanged); egui, C++ ImGui, and Tauri are brought to match. All gates green: deno check+lint+fmt
(Tauri), `make build` both C++ GUIs + clang-format, `make check-egui` + rustfmt.
**Priority:** 4 **Difficulty:** 2 (three front-ends; egui is the only sizeable change)
**Created:** 2026-11-01 (William Emerison Six <billsix@gmail.com>, from an on-display review; scope
widened from egui-only to egui+ImGui+Tauri on the maintainer's 2026-11-01 go-ahead). Supersedes the
earlier `egui-game-menu-for-new-game.md` (whose creation commit didn't land on master).

## BLUF

The three non-wx GUIs don't present New Game the way the wx trio does. Bring each to the wx shape — a
**Game menu** with a disc-count way to start a **New Game**, and a **New Game (Same Size)** entry that
restarts at the current count. Done = all four GUIs' Game menus carry both affordances with consistent
wording ("New Game (Same Size)"), each on-display-verified.

## The reference (wx trio, unchanged)

`ui/hanoi.xrc` `main_menubar` → **Game**: "New Game…\tCtrl+N" (prompts a disc count, 1–`MAX`=10, via a
NumberEntryDialog) + "New Game (Same &Size)\tCtrl+Shift+N" (reuse the current count) + Quit. Handlers in
`hanoigui.py` (`_on_new_game_prompt` / `_on_new_game_same`) and mirrored in `cpp/hanoiwx.cpp`.

## Per-front-end plan (each small)

1. **egui** (`rust/hanoi-egui/src/main.rs`) — biggest. Today: **no Game menu**; New Game is an inline
   `egui::DragValue(disc_count)` + "New game" button in the body (~lines 610–613). Add a **`Game`**
   `ui.menu_button` as the **first** item in the `egui::menu::bar` (left of Relabel) hosting: the
   disc-count `DragValue` (moved from the body), a **"New Game"** item (`new_game(disc_count)`), and a
   **"New Game (Same Size)"** item (`new_game(self.game.num_disks)`), each `ui.close_menu()` after. Remove
   the inline body control; re-check the goal-line/board layout still reads well.
2. **C++ ImGui** (`cpp/main.cpp` `draw_menubar`, the `BeginMenu("Game")` block) — today: a "New game
   (disks)" submenu (1–**8**) + "**Restart**" (= same size) + Quit. Rename to match wx: the submenu →
   **"New Game"** (keep it as the size picker) extended to **1–10** (`MAX_DISKS`); "Restart" →
   **"New Game (Same Size)"** (behaviour unchanged, `app.new_game(app.game.num_disks())`). Keep Quit.
3. **Tauri** (`rust/tauri/frontend/index.html` Game panel + `main.js`) — today: a `Discs` number input
   (1–10) + a "New Game" button, no same-size. Add a **"New Game (Same Size)"** button to the Game
   panel that `invoke("new_game", { discs: latest.num_disks })` (the backend `new_game(discs)` already
   exists; "same size" is just the current `num_disks` — no new command). Wire it like the existing
   `#newgame` handler (render the returned snapshot, close the menu).

## Verify

- egui: `cd rust && make check-egui` + `make egui` on a display.
- ImGui: `cd cpp && make build` + `make gui` on a display.
- Tauri: `cd rust && make type-check` (deno) + `make tauri` on a display.
- Each: New Game starts a fresh game at the chosen size; New Game (Same Size) restarts at the current
  size; both reachable from the Game menu. On-display sign-off before archive.

## Related

- `ui/hanoi.xrc` + `python/src/hanoigame/hanoigui.py` + `cpp/hanoiwx.cpp` — the wx reference.
- `tasks/reference/ui-design-principles.md` — tier/menu placement; this is a consistency fix within it.
- `tasks/reference/feature-spec.md` §6.2 (GUI menu guidance).
