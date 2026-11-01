# Make the Tauri frontend look native on Linux/GTK, macOS, and Windows (CSS design-token refresh)

**Status:** in progress — **steps 1 and 2 are committed** (token layer + board follows the OS
light/dark theme, on branch `desktop-native-look`). Step 3 (density) is deferred by the maintainer's
"keep current" decision, step 4 (toggle) is dropped, step 5 (window effects) is an optional spike. The
remaining action is the maintainer's **display pass** (`make tauri` on each OS). Not blocked.
**Priority:** 5 **Difficulty:** 4
**Created:** 2026-11-01 (William Emerison Six <billsix@gmail.com>). Comes out of the JS-options
investigation (`tasks/archive/2026/11/01/tauri-frontend-js-options.md`), which concluded **stay vanilla,
no framework** and named the real lever for "looks better / more desktop-y" as a **CSS design-system
pass**, not a dependency.

## BLUF

The Tauri frontend is 100% vanilla HTML/CSS/JS (confirmed 2026-11-01: `style.css` hand-written, 276
lines, no framework; `index.html` semantic; `main.js` strict-`checkJs`'d, no imports). It currently
ships a **single hard-coded dark theme** with a web-generic `system-ui` font. Goal: make it look like a
**native desktop app on Linux/GTK (the maintainer's host, matching the GTK wx GUIs), macOS, and
Windows**, while keeping every existing constraint — **no dependency, runs locally, no network,
statically verifiable**. The mechanism is a **CSS design-token layer** (semantic custom properties) with
**light + dark following the OS**, **per-platform native font stacks**, and **native-metric controls +
focus**. "Done" = the app reads as native on all three OSes (the maintainer verifies on each), the board
themes correctly, and nothing new is fetched or built.

## Context (read first)

- **Design authority:** `tasks/reference/ui-design-principles.md` (Apple-HIG-grounded; the three-tier
  flow) and `tasks/reference/feature-spec.md`. This task changes **look**, not information architecture
  or features — the tiers, panels, dialogs, and the canvas board all stay exactly as they are.
- **The frontend files:** `rust/tauri/frontend/{index.html,style.css,main.js}` + `deno.json`. Gated by
  `make type-check` (Deno `check --check-js` + `lint` + `fmt --check`) and `make format` — CSS/HTML are
  formatted by `deno fmt`, so re-run it after editing.
- **Constraints inherited from the parent investigation:** no npm/bundler, no CDN, offline, lean; the
  static check stays `deno`. A theme is CSS only — it adds nothing to fetch.

## The per-platform research (2026-11-01 — what "native" needs on each)

Tauri uses a **different webview per OS**, so the same CSS renders on three engines (sources at end):
- **Linux — WebKitGTK** (version varies by distro). This is the maintainer's host and where the **wx
  GUIs render via GTK/Adwaita**, so matching **GNOME Adwaita** palette/spacing makes the Tauri app look
  consistent with the sibling wx app. `system-ui` resolves to the GTK UI font (Cantarell/user's choice).
  WebKitGTK can **lag on new CSS** — so stick to broadly-supported features (custom properties,
  `prefers-color-scheme`, `accent-color` are all safe; **avoid `light-dark()`** and other very-new CSS
  until confirmed on the shipped WebKitGTK).
- **macOS — WKWebView** (WebKit, updates with the OS; old macOS lags). The San Francisco UI font comes
  from `-apple-system, BlinkMacSystemFont`. Native translucency/vibrancy is a **window** effect, not CSS
  — if wanted, it's a Tauri window-effects setting, out of scope for the CSS pass (noted as an option).
- **Windows — WebView2** (Chromium, recent — most CSS "just works"). The native font is **Segoe UI
  Variable**, which **must be named explicitly in CSS** (`"Segoe UI Variable", "Segoe UI"`). **Mica /
  Acrylic are DWM system materials a web page cannot use** — don't promise them; approximate with a flat
  translucent surface + `backdrop-filter: blur()` only if a frosted look is wanted. Fluent control
  metrics ≈ 4px corners, ~32px control height.

**The cross-platform font stack** (gives SF on macOS, Segoe UI Variable/Segoe on Windows, the GTK font
on Linux): `-apple-system, BlinkMacSystemFont, "Segoe UI Variable", "Segoe UI", system-ui, "Cantarell",
sans-serif`. Note `system-ui` has a known Windows locale bug (resolves to the *system-locale* UI font),
so the explicit `"Segoe UI …"` names are listed **before** `system-ui`.

**Accent color:** use the CSS **`accent-color` property** (with a theme token) to tint native form
controls (the disc-count `<input type=number>` spinner, any checkbox). The **`AccentColor` system-color
*keyword* is unreliable** (WebKit returns a constant; fingerprinting-scoped in Chromium) — so define our
own `--accent` token per theme rather than reading the OS accent.

## Plan

1. **[DONE — prototype committed] The token layer + light/dark + native fonts + focus.** Refactor
   `style.css` to a **semantic token layer** (`:root` custom properties for color/font/radius), swap
   every hard-coded hex for a `var(--…)`, add a **dark override under `@media (prefers-color-scheme:
   dark)`** (the current dark palette becomes the dark theme; a new tasteful **light** palette is the
   default), set **`color-scheme: light dark`** (so native scrollbars/controls/`<dialog>` backdrop
   follow), the **cross-platform native font stacks**, **`accent-color`**, and a visible
   **`:focus-visible`** ring. Decision logged: **the board (canvas + text `<pre>`) stays a fixed dark
   "screen" in both themes** — it's a graphic surface, not chrome, and keeping it fixed avoids a
   half-themed look until step 2. Layout/spacing unchanged so the diff is reviewable and nothing moves.
2. **[DONE 2026-11-01] Theme the canvas board in `main.js`.** The board colours are painted in JS, so
   CSS alone can't reach them. `main.js` now keeps a small `boardTheme` object refreshed by
   `refreshBoardTheme()`, which reads `--board-surface` (the canvas "desk") and `--fg-muted` (the
   reference-row text) from the token layer via `getComputedStyle(document.documentElement)`. Because the
   webview's `prefers-color-scheme` reflects the OS setting, those resolved tokens are already the active
   theme's, so the board follows light/dark; a `matchMedia("(prefers-color-scheme: dark)")` change
   listener repaints on a live OS flip. `style.css` gained light board tokens in `:root` + the dark ones
   in the dark `@media` block. The **wooden pegs/base and the vivid size-coloured discs stay
   theme-independent** (a physical toy's materials don't change with room lighting) — so only the desk
   surface and the text board flip. Stays typed (`@ts-check`, strict `checkJs`); gate green.
3. **[proposed] Native density + control metrics.** Optionally nudge the base size toward native
   (~14px) and adopt Fluent-ish control metrics (4px corners, ~32px control height) behind tokens;
   verify it still reads well on GTK/macOS. Left as its own step because it shifts every measurement —
   the maintainer should see step 1 first.
4. **[proposed] Optional manual theme toggle.** Add `:root[data-theme="light"|"dark"]` override hooks +
   a tiny toggle (View menu) so the user can override the OS setting. Pure DOM + a `localStorage` read;
   stays typed and offline. Only if wanted — `prefers-color-scheme` alone already follows the OS.
5. **[proposed] Optional native window effects.** macOS vibrancy / a subtle Windows backdrop are **Tauri
   window settings**, not CSS — note as a separate small spike if the maintainer wants true translucency
   (cannot be done from the web layer).
6. **Verify** (per step): `make type-check` + `make format` stay green (CSS/HTML are `deno fmt`'d);
   **the maintainer runs `make tauri` on Linux and, when available, macOS + Windows** and confirms the
   look on each (the agent can't drive those displays). Re-run the no-network check once
   `tasks/tauri-frontend-no-network-static-gate.md` lands (the token pass adds no remote refs — verified
   none in this prototype).

## Open questions — all resolved by the maintainer 2026-11-01 (William Emerison Six <billsix@gmail.com>)

1. ~~Board theming: follow light/dark, or stay a fixed dark "screen"?~~ **Decided: follow the OS
   light/dark setting** ("if you can query the desktop and use light dark based off of what it's
   configured for, then do that"). We can: the webview's `prefers-color-scheme` reflects the desktop's
   configured theme on all three OSes, so `main.js` reads the resolved `--board-surface` / `--fg-muted`
   tokens at paint time and the board's desk surface + label text flip with the theme. **Step 2 done**
   (the wooden pegs/base and vivid disc colours stay theme-independent — a toy's materials don't change
   with room lighting).
2. ~~Native density: nudge to ~14px + Fluent metrics, or keep current?~~ **Decided: keep current for
   now** (maintainer: "whatever you recommend" → my recommendation). Reason unchanged: step 3 shifts
   every measurement, so it's better tuned once the maintainer has seen steps 1–2 rendered. **Step 3
   stays proposed**, available on request after the display pass.
3. ~~Manual theme toggle: add one, or is OS-follow enough?~~ **Decided: no toggle** (maintainer: "what
   you recommend" → my recommendation). `prefers-color-scheme` follows the OS, which is the native
   behaviour; a toggle adds DOM + `localStorage` state for little gain. **Step 4 dropped** unless later
   wanted.
4. ~~Light vs dark default?~~ **Decided: follow the OS** ("same answer as 1") — light default, dark under
   the OS dark setting. Already the prototype's behaviour; no change.

## Related

- Parent: `tasks/archive/2026/11/01/tauri-frontend-js-options.md` (the "stay vanilla, improve CSS"
  decision + option 6 / library research).
- `tasks/reference/ui-design-principles.md`, `tasks/reference/feature-spec.md` — the look must preserve
  the tiers/features unchanged.
- The JS static gate alongside which CSS/HTML are checked:
  <https://github.com/billsix/runClaudeInContainer/blob/master/tasks/reference/javascript-coding-standard.md>.
- No-network gate (verifies the theme adds nothing remote): `tasks/tauri-frontend-no-network-static-gate.md`.

## Sources (per-platform native look, verified 2026-11-01)

- Tauri v2 webview per OS (WKWebView / WebView2 / WebKitGTK; feature lag):
  <https://v2.tauri.app/reference/webview-versions/>
- Windows typography — Segoe UI Variable, "specify it in CSS":
  <https://learn.microsoft.com/en-us/windows/apps/design/style/typography> ; Windows design hub:
  <https://developer.microsoft.com/windows/design>
- System font stack history + the Windows `system-ui` locale caveat:
  <https://css-tricks.com/snippets/css/system-font-stack/>, <https://samthor.au/2020/system-font/>
- `accent-color` property + `AccentColor` keyword limits (WebKit constant, Chromium scoping):
  <https://developer.mozilla.org/en-US/docs/Web/CSS/accent-color>,
  <https://developer.mozilla.org/en-US/docs/Web/CSS/system-color>
- GNOME Adwaita for the GTK-consistent look (extract CSS variables/palette):
  <https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/styles-and-appearance.html>,
  <https://github.com/rickbot-dot/adwaita.css>
