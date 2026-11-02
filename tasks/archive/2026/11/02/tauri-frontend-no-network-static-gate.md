# Add a static "no-network" gate for the Tauri frontend

**Status:** DONE 2026-11-02 (William Emerison Six <billsix@gmail.com>) — staged, not committed
(stage-only default). Ready to archive after the maintainer's work commit. This task is also the
template the two sibling gates adapted (they landed in the **same change**).
**Priority:** 6 **Difficulty:** 2
**Parent:** `tasks/archive/2026/11/01/tauri-frontend-js-options.md` (investigation, COMPLETE + archived
2026-11-01). This is the one
concrete change that investigation recommended: everything else was "already done, stay the course."
**Created:** 2026-11-01 (William Emerison Six <billsix@gmail.com>).

## BLUF

The maintainer's hard constraint on the Tauri frontend is **it must run entirely locally, with no
network**, and they want to **verify that statically**. Today the frontend (`rust/tauri/frontend/`) in
fact references nothing remote, and Tauri embeds it as local assets — but **nothing enforces that it
stays that way**: a future edit could add a CDN `<script>`, a web-font `@import`, an `<img>` from a URL,
or a `fetch()` to a remote host, and no gate would catch it. "Done" = a cheap, fast static check, wired
into `make type-check` (or its own `make` target) and CI, that **fails if any frontend file references a
remote resource**, plus a documented one-command runtime proof (run the app offline). No new
dependency, no network, no Node.

## Context (read first)

- **Current state (verified 2026-11-01):** `frontend/main.js` (607 lines, `// @ts-check`, strict Deno
  `checkJs`), `index.html`, `style.css`, `deno.json`. A grep for `https?://` / `src="//"` across
  `frontend/` returns **nothing** — so the gate starts green. Tauri embeds `frontend/` via
  `generate_context!` (`tauri.conf.json`), so the webview loads only compiled-in local assets.
- **Why a gate and not just trust:** the no-network property is a *standing invariant*, exactly the kind
  the maintainer wants enforced mechanically rather than re-audited by eye (cf. the house
  "instrumentation / make the machine tell you the truth" preference). A static grep is O(ms) and has no
  deps — it fits the "no Node, offline, lean" constraints the parent task documents.
- **Scope:** the Tauri frontend only. (The C++ wasm build and the egui-web build are separate web
  targets with their own asset stories — out of scope here; if the maintainer wants the same guarantee
  there, spin siblings.)

## What "references a remote resource" means (what the gate must catch)

Fail on any of these appearing in `frontend/*.{js,html,css}` (allow-list the genuine exceptions
in-script, with a reason):
- `http://` / `https://` / protocol-relative `//host/...` in `src=`, `href=`, `url(...)`, `@import`,
  `import ... from "http..."`.
- `fetch(` / `XMLHttpRequest` / `new WebSocket(` / `EventSource(` to a non-local target (any absolute
  URL; a same-origin relative path is fine — though this frontend uses Tauri `invoke`, not HTTP).
- A web-font or stylesheet `@import` / `<link rel="stylesheet">` to a URL.
- **Allowed:** relative paths (`main.js`, `./style.css`), `data:` URIs, the `window.__TAURI__` global,
  and Tauri `invoke(...)` (local IPC, not network). The `tauri.conf.json` CSP, if set, is a second line
  of defence but is not a substitute for the static check.

## Plan (decide the mechanism with the maintainer — see open questions)

1. Write `rust/tauri/tools/check-no-network.sh` (or fold into `format.sh`/the type-check step): a
   `rg`/`grep -nE` over `frontend/` for the patterns above, printing offenders with `file:line`, exiting
   non-zero if any are found. Multi-pattern but single-command, so it is safe-by-shape on exit status
   (one `grep`); if it grows to several passes, use the `status=0; … || status=1; exit $status` shape
   (house rule for multi-step gates).
2. Wire it into **`make type-check`** (decided 2026-11-01, maintainer): fold the check into the existing
   static-gate target that already runs the Deno checks over the frontend — accumulate its exit status
   with the Deno steps (`status=0; … || status=1; … exit $status`), so one run reports all the red. No
   new `make` target and no new CI job (it rides the `rust-type-check` job).
3. Add it to CI in the **`rust-type-check`** job (where the frontend's Deno checks already run) so it
   gates every push/PR — one line, matching the "CI is a thin wrapper over `make`" principle
   (`tasks/reference/ci-github-actions.md`).
4. Document the **runtime proof** in `rust/CLAUDE.md` (or the Tauri section): build the app and run it
   with the network cut, confirming the UI renders fully from embedded assets — the "offline-export
   test" shape from the personal overlay's "Self-contained images + live source".
5. Verify the gate: it passes on the current (clean) tree; add a throwaway `<script src="https://x">`
   and confirm it fails with the right `file:line`; remove it.

## Open questions

*(Both resolved by the maintainer 2026-11-01.)*

1. ~~Wiring: fold into `make type-check` or a standalone target?~~ **Decided: fold into `make
   type-check`** (rides the existing `rust-type-check` CI job; no new target/job). Reflected in Plan
   step 2.
2. ~~Scope the other web targets now or later?~~ **Decided: now** — sibling tasks scaffolded for the
   **C++ wasm** gate (`tasks/archive/2026/11/02/cpp-wasm-no-network-static-gate.md`) and the **egui-web** gate
   (`tasks/archive/2026/11/02/egui-web-no-network-static-gate.md`). This task is the proven template they adapt; the one
   real per-target difference is the glob scope (and, for C++, **excluding the vendored emacs `elpa/`
   tree**, which legitimately contains CDN links inside third-party packages that never ship in the
   app).

3. **(New, optional) Shared gate script?** The three gates differ only in target dir + globs — the check
   logic is identical. Worth a single reusable `tools/check-no-network.sh` (arg: a dir + glob) vendored
   across the subprojects, like `check_local_annotations.py`? Or keep three tiny per-subproject copies
   until a 3rd consumer proves the need (the house "inline until 2–3 real consumers" bar)? Recommend
   starting with per-subproject copies and promoting only if they drift into wanting one source. Your
   call.

## Done — what was built (2026-11-02)

Implemented across all three web targets in one change (this task + the two siblings).

- **Scripts (2 copies, per-subproject — OQ3 resolved):** `rust/tools/check-no-network.sh` (covers
  **both** Rust web targets: the Tauri frontend `tauri/frontend/*.{html,js,css}` and the egui-web source
  `hanoi-egui/{index.html,Trunk.toml}`) and `cpp/tools/check-no-network.sh` (`cpp/shell.html`). **Not** a
  shared vendored script: the logic is ~8 lines of grep and hanoi prizes subproject self-containment;
  only two subprojects need it. Promote to a shared vendored script (à la `check_local_annotations.py`)
  only if a 3rd subproject appears. Both scripts are portable (run in-container or host-side) and
  committed executable (`git add --chmod=+x`).
- **Pattern:** fails on `http(s)://` / `ws(s)://` anywhere, and protocol-relative `//host` in
  `src=`/`href=`/`url(…)`. Allowed: relative paths, `data:` URIs, Tauri `invoke()`/`window.__TAURI__`,
  and Trunk's `data-trunk` directive (no scheme). A URL in a *comment* trips it too (conservative);
  allow-list genuine exceptions in-script with a reason. Single-pattern grep → safe-by-shape on exit.
- **Wiring (OQ1/OQ2 resolved):** Rust folded into `make type-check` (accumulates exit status with the
  Deno steps, in-container; rides the existing `rust-type-check` CI job — no new job, per the recorded
  2026-11-01 decision). C++ got a standalone `make check-no-network` that runs the grep **host-side**
  (no `image` dep) + a new `cpp-check-no-network` CI job — deliberately not behind `image` so CI needn't
  build the ~1.5 GB emsdk image to grep one file.
- **Docs:** `rust/CLAUDE.md`, `cpp/CLAUDE.md`, and the root `CLAUDE.md` target/CI lists updated; the
  offline runtime-proof noted in each subproject `CLAUDE.md`.
- **Verified (host-side, 2026-11-02):** green on the clean tree (exit 0); injecting a `<script
  src="https://…">` into `tauri/frontend/index.html`, a protocol-relative `<link href="//…">` into
  `hanoi-egui/index.html`, and a remote `<script>` into `cpp/shell.html` each made the right gate FAIL
  (exit 1) with the offending `file:line`; `git checkout` restored all three and the gates went green
  again. Make/CI wiring verified by inspection (not run — would build the subproject images).

## Related

- Parent investigation: `tasks/archive/2026/11/01/tauri-frontend-js-options.md` (findings + why this is
  the only recommended change).
- Sibling gates (same pattern, other web targets): `tasks/archive/2026/11/02/cpp-wasm-no-network-static-gate.md`,
  `tasks/archive/2026/11/02/egui-web-no-network-static-gate.md`. This task is their template.
- `tasks/reference/ci-github-actions.md` — where the CI line lands (the `rust-type-check` job).
- Personal overlay "Self-contained images + live source" — the offline guarantee this statically
  enforces for the web frontend; its runtime-proof is the offline-run test.
- The JS static-check gate it rides alongside:
  <https://github.com/billsix/runClaudeInContainer/blob/master/tasks/reference/javascript-coding-standard.md>
  (Deno `check`/`lint`/`fmt`, no `node_modules`).
