# Win celebration vs the rebinding dialog — two windows at once (GUI)

**Status:** decided 2026-11-01 (William Emerison Six <billsix@gmail.com>) — **option 5** (the
save-on-New-Game hybrid): first-win teaching modal kept, later wins a lightweight status line, the Save
offer moved to the new-game / discard boundary (suppressed on apply-wins and when already saved), applied
across all GUIs; text UIs keep showing everything inline at the win. **Implementing** on branch
`win-celebration-recipe-discovery`. The UX write-up: `tasks/reference/win-celebration-and-recipe-discovery-ux.md`.
**Priority:** 5 **Difficulty:** 3
**Created:** 2026-11-01 (William Emerison Six <billsix@gmail.com>). Found during the display-verify of
the win-celebration work (`tasks/win-celebration-recipe-discovery.md`): in the wxPython GUI, a recipe
**apply under a relabelling that also won** opened the three-panel rebinding window **and** the win
celebration modal at the same time — confusing.

## BLUF

On a GUI win that coincides with the §4.8 **three-panel rebinding dialog** — i.e. a *relabelled* winning
move or recipe-apply — two windows open at once: the **modeless** rebinding view (`dlg.Show()`) and then
the **modal** celebration (`dlg.ShowModal()`). Decide how to resolve it and apply the fix **consistently
across all GUIs**. **Text UIs are exempt** — a CLI/TUI prints sequentially, with no window stacking, so
it can keep showing everything (the rebinding table, then the celebration, then the save prompt) in
order; this is a GUI-only problem.

## Context (the mechanism)

- `hanoigui.py`: `_apply_recipe_by_name` / `_on_move`, when relabelled, call `_show_rebinding_dialog(...)`
  (modeless `Show()`, ~line 784) and then `if is_won(): _on_win()` (modal `ShowModal()`, ~line 986).
- **The first win never collides.** You can't relabel-win or apply-win before your first win (a recipe
  needs a prior win to exist, and relabelling has no use yet), so the **first win is always a clean
  hand-solve under the default labelling** — no rebinding dialog. The collision only happens on a
  **later** win under a relabelling, which is exactly the win that least needs the recipe *teaching*.
- Same shape in the **Rust** and **C++ wx** GUIs (two dialog windows). In **Tauri** and **egui** the
  rebinding view is an inline panel, so the collision is "modal/window over a panel" — milder, but still
  overlapping and worth fixing for consistency.

## Options (all logged; see the decision below)

1. **Suppress the celebration when a rebinding window is shown this action.** The rebinding view is the
   teaching surface for a relabelled win; don't stack a second. Win registers in the status bar, Tier-2
   still unlocks. Smallest change. *Cost:* no one-click Save on those wins (use the Recipe menu).
2. **Sequence — celebration *after* the rebinding dialog closes.** Keep the celebration on every win, but
   when a rebinding window is up, fire the celebration from its close event (GUIs with a close event) or
   via a latch (immediate-mode egui/ImGui). No overlap, save-offer preserved. *Cost:* more wiring;
   two windows to dismiss in a row; "after close" is awkward in immediate-mode.
3. **Merge a "Solved! Save as recipe?" footer into the rebinding dialog** for a winning relabelled
   action, and skip the separate celebration — one window. *Cost:* most work; the rebinding layout is the
   shared `RebindingDialog` XRC, so a conditional footer is invasive; only helps the relabelled case.
4. **Make the celebration non-modal everywhere** (an in-window banner, not a dialog) so it never competes
   as a separate window. *Cost:* loses the deliberate "stop and notice" modal that works well for a
   normal clean win; biggest behavioral change.
5. **(New, under evaluation) Decouple the save from the win — offer it at New Game.** On winning, the
   celebration becomes congrats + (first-win) teaching only, **no Save button**; when the player chooses
   **New Game** after a won-and-unsaved game, offer "Save your solution as `solve-<N>` before starting
   over?". "Save before discarding" is a natural, familiar pattern, and it removes the save prompt from
   the crowded win moment entirely. **Strongest form (hybrid):** keep the **first-win teaching modal**
   (it never collides — first win is always a clean default solve), make **later wins** a lightweight
   status line (no competing window), and move the **Save offer to New Game**. *Costs:* save is decoupled
   from the win; a won game the player never follows with New Game (they just quit) is never offered the
   save (minor — recipes are a convenience, not precious data); on an **apply-win** the New-Game save
   offer is odd (suppress when the finished solution was produced by applying a recipe); it shifts the
   save teaching off the spec's "win is the teaching hinge" (§3.5) onto the New-Game boundary.

## Open question

1. Which approach — **(2)** sequence the celebration after the rebinding dialog closes (the current
   lean), or **(5)** the save-on-New-Game hybrid (first-win teaching kept, later wins lightweight, Save
   moved to New Game)? Whichever: **apply it across all GUIs**, and **leave the text UIs showing
   everything sequentially** (no change needed there).

## Related

- `tasks/win-celebration-recipe-discovery.md` (+ the python/rust/cpp children) — the feature this refines.
- `tasks/reference/feature-spec.md` §4.8 (rebinding view), §4.9 (win celebration), §4.5 (save prompt),
  §3.5 (the learning flow / "win is the teaching hinge").
