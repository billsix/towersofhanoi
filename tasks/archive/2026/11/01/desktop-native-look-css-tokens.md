# Make the Tauri frontend look native on Linux/GTK, macOS, and Windows (CSS design-token refresh)

**Status:** DONE 2026-11-01 — steps 1 (token layer) and 2 (board follows OS light/dark) committed on
branch `desktop-native-look`; the maintainer reviewed the Linux result ("looks good") and chose to
**assume macOS/Windows are fine and reopen this if they aren't**. Durable design rationale harvested to
`tasks/reference/tauri-frontend-native-look.md`.
**Priority:** 5 **Difficulty:** 4
**Created:** 2026-11-01 (William Emerison Six <billsix@gmail.com>). Out of the JS-options investigation
(`tasks/archive/2026/11/01/tauri-frontend-js-options.md`), which concluded **stay vanilla, no framework**
and named a **CSS design-system pass** as the real lever for "looks better / more desktop-y."

## What was done

1. **Token layer + light/dark + native fonts + focus** (`style.css`). Refactored the hand-written CSS to
   a semantic `:root` custom-property layer (colour/font/radius), light default + dark under
   `@media (prefers-color-scheme: dark)`, `color-scheme: light dark`, the cross-platform native font
   stacks (SF / Segoe UI Variable / GTK), `accent-color`, a `:focus-visible` ring. Layout unchanged.
2. **Board follows the OS light/dark theme** (`main.js`). The canvas board reads `--board-surface` and
   `--fg-muted` from the token layer via `getComputedStyle`; the webview's `prefers-color-scheme` is the
   desktop's configured theme, so the board tracks it, and a `matchMedia` listener repaints on a live
   flip. Wooden pegs/base and vivid discs stay theme-independent; only the desk surface + text board flip.

All typed (`@ts-check`, strict `checkJs`); `make type-check` (Deno check/lint/fmt) + `make format` green.
No remote references added (the no-network invariant holds).

## Maintainer's decisions (2026-11-01, William Emerison Six <billsix@gmail.com>)

- **Board theming:** follow the OS light/dark setting. Done (step 2).
- **Native density (~14px / Fluent metrics):** keep current for now — deferred, not done.
- **Manual theme toggle:** none; OS-follow is enough.
- **Light vs dark default:** follow the OS (light default, dark under OS dark).
- **macOS/Windows verification:** assumed fine; reopen this task if a real device shows otherwise.

## If reopened / future options

The per-platform facts and the two deferred options (native **density**, native **window effects** —
macOS vibrancy / Windows Mica, which are Tauri *window* settings, not CSS) are described in
`tasks/reference/tauri-frontend-native-look.md`. Start there.

## Related

- `tasks/reference/tauri-frontend-native-look.md` — the durable design rationale this harvested into.
- Parent: `tasks/archive/2026/11/01/tauri-frontend-js-options.md` (the "stay vanilla, improve CSS" decision).
- `tasks/reference/ui-design-principles.md` — the information architecture this look preserves unchanged.
- No-network gate (enforces the theme adds nothing remote): `tasks/tauri-frontend-no-network-static-gate.md`.
