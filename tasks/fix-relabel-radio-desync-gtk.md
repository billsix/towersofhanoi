# Fix: wx GUI relabel radio desync ("second relabel does nothing until I pick another")

**Status:** fix applied (2026-09-15) — **awaiting human GUI verify** at n=5
**Priority:** 3
**Difficulty:** 3

## BLUF

In the wx GUI, a relabel to a permutation could do nothing — consistently reproduced (maintainer,
2026-09-15): solve n=3 with 3 relabels + save, solve n=4 with 3 relabels + save, start n=5, first
relabel works but relabeling to `2 1 3` does nothing. **Real root cause:** the six permutations were
**radio** menu items, and **wxGTK emits NO event at all when you click the radio it already thinks is
active** — so the click never reaches Python and `_on_relabel_menu` never runs. n=4's last relabel left
GTK's active radio on `2 1 3`; that state persisted across into n=5, so the n=5 click on `2 1 3` was
swallowed. **Fix:** make the six items **normal (non-radio) menu items** — normal items always emit on
every click — and show the active one with a leading bullet in the label. "Done" = the maintainer's
exact repro relabels to `2 1 3` on the first click.

## Why it happens (diagnosis)

The model/dispatch layer is provably correct (verified 2026-09-15): `current_labels` in `_refresh`
(`change_labels_on_pegs(labelling, i)+1` per peg) equals the tuple key in `presenter._LABELLING_BY_TUPLE`
for that labelling, so the right item was always identified. The bug was entirely wxGTK radio semantics:

- **wxGTK emits NO event when the user clicks the radio item GTK already considers active.** The click
  is swallowed *before Python sees it* — `_on_relabel_menu` never fires.
- GTK's "active radio" persists across `_new_game` and drifts from the model (the win→new-game
  enable/disable cycling and programmatic re-checks don't reliably move it), so the item GTK thinks is
  active is often *not* the model's labelling.

This is why the first two fix attempts **could not work**: both operated *after* the event arrived
(guarding / re-asserting `Check()` in `_refresh`), but the failing click produces **no event**, so no
handler-side logic can rescue it. In the maintainer's repro, `2 1 3` was the last labelling used in
n=4, so GTK held it active into n=5; clicking `2 1 3` there produced nothing, while clicking any
*other* permutation forced a real toggle (which did emit) and "worked".

## The fix (applied)

Stop using radio items for the relabel group — a normal `wxMenuItem` emits `wx.EVT_MENU` on **every**
click, killing the whole failure class:

- `python/src/hanoigame/hanoi.xrc`: removed `<radio>1</radio>` from the six `relabel_*` items (with a
  comment on why); they are now normal menu items.
- `python/src/hanoigame/hanoigui.py`:
  - `_build_menu_bar`: also caches each item's base label (`relabel_base_labels`) for the indicator.
  - `_refresh`: replaced the radio `Check()` logic with a display-only label rewrite — a leading
    `●  ` bullet on the active item, spaces on the rest (`SetItemLabel`, which never emits an event).
  - Removed the `_syncing_relabel` flag (init + `__init__`) and the early-return in `_on_relabel_menu`
    — both existed only to tame the radio's spurious `Check()` event, which no longer happens.

The board-style Text/Graphics items stay radio (only two, `_swap_renderer` early-returns on no-op, and
switching always changes state — the maintainer confirmed they work; left alone to limit churn). Note
the same latent trap exists there in principle.

Reference-doc gotcha rewritten in `tasks/reference/architecture-overview.md` (the radio approach and
its two failed patches are superseded).

**Verified here:** compiles, ruff clean, 124 tests pass (the model layer; the GUI itself isn't
importable in the agent sandbox — no wxPython).

## Human verify (the only remaining step)

Run `hanoi-gui` and reproduce the exact failing sequence:
1. Solve n=3 using 3 relabels; save.
2. Solve n=4 using 3 relabels (ending on `2 1 3`); save.
3. Start n=5; relabel once (works), then relabel to **`2 1 3`** — it must take on the first click now.
4. Sanity: the **Relabel pegs** menu shows a `●` bullet next to the currently-active peg order, and it
   moves as you relabel.

If a relabel *still* fails after this, that would be genuinely surprising (the event should now always
fire) — capture the sequence and we instrument `_on_relabel_menu` with a `DBG` stderr print (per
`~/.claude/reference/print-debugging.md`) to confirm whether the click reaches Python at all.

## Related

- `python/src/hanoigame/hanoigui.py` (`_refresh`, `_on_relabel_menu`, `__init__`).
- `tasks/reference/architecture-overview.md` — the wxGTK radio-menu gotcha (updated).
- `tasks/archive/2026/09/14/record-recipe-bindings-and-show-rebinding.md` — where the earlier
  (partial) relabel fix landed.
