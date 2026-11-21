# ASCII-art indentation in the Rust UIs (done 2026-11-21)

**Priority:** 5 **Difficulty:** 3
**Created:** 2026-11-05; **done:** 2026-11-21 (William Emerison Six <billsix@gmail.com>); branch
`gui-batch-2026-11-21`.

## What was found

The Rust wx GUI's **text board** (`rust/hanoi-gui/src/main.rs`, the `board_text` `TextCtrl`) was drawn in
the default proportional font. Reproduced on screen under Xvfb: with the text board selected, the pegs,
discs and label row drifted out of their columns, and the board sat left of centre because
`centred_board_text` pads by `get_char_width()`, which is an average width in a proportional font. This
was the lead recorded when the task was written, confirmed.

The other Rust text views were already fine, checked 2026-11-21:

- wx history list, recipe dialog (`show_monospace_dialog`) and rebinding view: teletype font.
- TUI (`rust/hanoi`): every board line is `presenter::total_width(n)` wide (the
  `board_lines_match_presenter_width` test asserts it), so per-line centring keeps the columns.
- egui: the board is painted graphics; the text views use `monospace`.
- Tauri: the board is a `<pre>` with the `--font-mono` stack.
- No `trim()` touches any rendered line.

## What was done

- `monospace_font()` in `rust/hanoi-gui/src/main.rs`: one helper for the 11 pt teletype font, now set on
  the text board too, and used by the history list, the recipe dialog and the rebinding view.
- `tasks/reference/feature-spec.md` §6.2 now says every text view with aligned columns uses a
  fixed-width font, with compliance row 22.

## Verification

- Before/after screenshots of the text board (Xvfb, driven by clicks): after the fix the columns line up
  and the board is centred, matching the Python wx text board. The click script and its image are
  `tasks/adhoc/rust-ui-ascii-art-indentation/shot.sh` and `Containerfile` (one-shot, removed at
  archive). The same run showed the history-review mode of the previous task working on screen.
- Rust gates green: `format`, `check --workspace --all-targets`, `test --workspace`, the egui and Tauri
  `cargo check`s, and the Deno type-check.
