# Tauri frontend — making it look native (CSS design-token layer, OS light/dark)

Durable design notes for the look of the Tauri desktop app's webview UI
(`rust/tauri/frontend/{index.html,style.css,main.js}`). States what is **true now**
and the per-platform facts behind it; the work that produced it is archived at
`tasks/archive/2026/11/01/desktop-native-look-css-tokens.md` (and its parent, the
JS-options investigation, at `tasks/archive/2026/11/01/tauri-frontend-js-options.md`).

**Scope:** this is the *look* (colour/font/theme). The information architecture — the
three-tier learning flow, panels, dialogs, the canvas board layout — is
`tasks/reference/ui-design-principles.md` and is unchanged by any of this. Cross-project
Tauri mechanics (IPC boundary, build deps) are in runClaudeInContainer
`tasks/reference/tauri-desktop-apps.md`.

## The frame (why vanilla CSS, not a framework)

The JS-options investigation (2026-11-01) concluded **stay vanilla — no framework, no
dependency**: the frontend is already 100% vanilla HTML/CSS/JS, `@ts-check`'d under strict
Deno `checkJs`, with drag-drop done in Canvas + PointerEvents and no remote URLs. "Looks
better / more desktop-y" is therefore a **CSS design-system job**, not a library adoption.
Every change here is pure CSS + a small typed JS read — **no new dependency, nothing
fetched, nothing built**, so the maintainer's hard constraints (runs locally, no network,
statically verifiable) are preserved.

## Per-platform reality: one CSS, three webviews

Tauri uses a **different webview per OS**, so the same CSS renders on three engines:

- **Linux — WebKitGTK** (version varies by distro). This is the maintainer's host and where
  the sibling **wx GUIs render via GTK**, so matching the GTK look keeps the Tauri app
  consistent with them. `system-ui` resolves to the GTK UI font (Cantarell / the user's
  choice). WebKitGTK can **lag on new CSS** → stick to broadly-supported features (custom
  properties, `prefers-color-scheme`, `accent-color`, `:focus-visible` are all safe);
  **avoid `light-dark()`** and other very-new CSS until confirmed on the shipped WebKitGTK.
- **macOS — WKWebView** (WebKit, updates with the OS; old macOS lags). The San Francisco UI
  font comes from `-apple-system, BlinkMacSystemFont`. Native translucency/vibrancy is a
  **window** effect, not CSS (see "Future options").
- **Windows — WebView2** (Chromium, recent — most CSS "just works"). The native font is
  **Segoe UI Variable**, which **must be named explicitly in CSS**; `system-ui` alone has a
  known Windows **system-locale bug** (resolves to the locale UI font), so the explicit
  `"Segoe UI Variable", "Segoe UI"` names are listed **before** `system-ui`.

### The native font stack

`-apple-system, BlinkMacSystemFont, "Segoe UI Variable", "Segoe UI", system-ui,
"Cantarell", "Noto Sans", sans-serif` — gives SF on macOS, Segoe UI Variable/Segoe on
Windows, the GTK font on Linux. Monospace (board text, status, history): `ui-monospace,
"SF Mono", "Cascadia Code", "Consolas", "Menlo", "Source Code Pro", monospace`.

### Accent colour

Use the CSS **`accent-color` property** fed by a theme token (`--accent`) to tint native
form controls (the disc-count `<input type=number>` spinner, etc.). Do **not** read the OS
accent via the `AccentColor` system-color *keyword* — WebKit returns a constant and
Chromium fingerprint-scopes it, so it's unreliable; define our own `--accent` per theme.

## How it's built: the semantic token layer

`style.css` is a **semantic design-token layer** — `:root` custom properties for
colour/font/radius, every value referenced as `var(--…)`, no bare hex in the rules.

- **Light is the default** (`:root`); **dark overrides under `@media (prefers-color-scheme:
  dark)`**. This follows the OS and is the native convention.
- **`color-scheme: light dark`** on `:root` makes native scrollbars, form controls, and the
  `<dialog>` backdrop follow the OS too.
- Tokens are grouped: page/surface backgrounds, foreground (`--fg` / `--fg-muted` /
  `--fg-subtle`), borders, control fills + hover, field background, `--accent`, `--status`,
  `--shadow`, `--backdrop`, and the **board tokens** (below).
- A visible **`:focus-visible`** ring (native desktop apps always show keyboard focus) and a
  `button:active` state.

## The canvas board follows the OS theme too

The board is drawn on a `<canvas>` in `main.js` (a mirror of the wxDragon DC board), so CSS
alone can't reach its painted colours. The mechanism that makes it theme:

- `main.js` keeps a small `boardTheme` object refreshed by `refreshBoardTheme()`, which
  reads **`--board-surface`** (the canvas "desk" background) and **`--fg-muted`** (the
  relabelling reference-row text) from the token layer via
  `getComputedStyle(document.documentElement)`.
- Because the **webview's `prefers-color-scheme` reflects the desktop's configured theme on
  all three OSes**, those *resolved* token values are already the active theme's — so
  reading them is how the app "queries the desktop." No OS-specific API is needed.
- A `matchMedia("(prefers-color-scheme: dark)")` **change listener repaints** the board on a
  live OS flip while the app is open.
- **Theme-independent on purpose:** the wooden base/pegs and the vivid size-coloured discs
  (and the label-badge colours) are painted from fixed JS constants — a physical toy's
  materials don't change with room lighting. Only the **desk surface** and the **text
  board** (`<pre>`, via CSS `--board-bg`/`--board-fg`) flip. Board tokens therefore have a
  light set in `:root` and the original dark set in the dark `@media` block.

## The no-network / static-verify constraints

The theme adds **nothing remote** (verified: a grep for `https?://` / `src="//"` / `fetch(`
/ `@import` across `frontend/` returns nothing). Keeping it that way is a standing invariant
the maintainer wants enforced mechanically — see `tasks/archive/2026/11/02/tauri-frontend-no-network-static-gate.md`
(and the C++ wasm / egui-web siblings). The look pass rides the existing frontend gate:
`make type-check` (Deno `check --check-js` + `lint` + `fmt --check`) and `make format`
(`deno fmt`) over the three static files.

## Future options (researched, deliberately not done)

Available if the maintainer (William Emerison Six <billsix@gmail.com>) later wants them;
neither is a standing recommendation:

- **Native density / control metrics.** Nudge the base size toward native (~14px) and adopt
  Fluent-ish metrics (4px corners, ~32px control height) behind tokens. Deferred because it
  shifts *every* measurement — better tuned against a live render. Decision 2026-11-01: keep
  current sizing.
- **Native window effects.** macOS **vibrancy** and a Windows backdrop are **Tauri window
  settings, not CSS** — the web layer can't produce them. Windows **Mica/Acrylic are DWM
  system materials a web page cannot use**; the closest CSS approximation is a flat
  translucent surface + `backdrop-filter: blur()`. A separate small spike if wanted.

A manual light/dark **toggle** was considered and **declined** (2026-11-01): `prefers-color-scheme`
following the OS is the native behaviour, and a toggle adds DOM + `localStorage` state for
little gain.

## Sources (verified 2026-11-01)

- Tauri v2 webview per OS: <https://v2.tauri.app/reference/webview-versions/>
- Windows typography (Segoe UI Variable, "specify it in CSS"):
  <https://learn.microsoft.com/en-us/windows/apps/design/style/typography>
- System font stack + the Windows `system-ui` locale caveat:
  <https://css-tricks.com/snippets/css/system-font-stack/>, <https://samthor.au/2020/system-font/>
- `accent-color` property + `AccentColor` keyword limits:
  <https://developer.mozilla.org/en-US/docs/Web/CSS/accent-color>,
  <https://developer.mozilla.org/en-US/docs/Web/CSS/system-color>
- GNOME Adwaita (GTK-consistent palette):
  <https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/styles-and-appearance.html>

_Reference doc created 2026-11-01 (William Emerison Six <billsix@gmail.com>), harvested from
the `desktop-native-look-css-tokens` task at archive._
