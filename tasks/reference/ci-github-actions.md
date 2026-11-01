# CI — GitHub Actions (format / test / type-check per subproject)

Durable description of hanoi's continuous-integration setup: what runs, where, and the principles
behind it. The CI itself lives in **`.github/workflows/checks.yml`** (on every push + pull request);
this doc is the *why* and the map. Read it before changing CI, adding a subproject, or wondering "is
this gated?". (It states what IS; history is in git + the archived task
`tasks/archive/2026/10/27/github-actions-format-test-typecheck-ci.md`.)

## Governing principle: CI is a thin wrapper over each subproject's `make`

Every CI job is just `actions/checkout` → `cd <subproject> && make <target>`. **All the logic lives in
the Makefiles/Dockerfiles**, so the *identical* command runs locally and in CI — CI can never drift
from `make`, and a red CI job reproduces with one local `make`. Each subproject's `CONTAINER_CMD`
auto-detects `podman` → `docker`, so the same containerized target runs on the GitHub `ubuntu-latest`
runner (Docker) and on the maintainer's podman host. (Sibling: `github.com/billsix/geometricalgebra`
`.github/workflows/checks.yml` follows the same thin-wrapper shape, plus a `lean.yml`. The
`modelviewprojection` checkout has no `.github/` — it is not a CI reference despite sometimes being
cited as one.)

Jobs **never modify the repo**: `make check-format` runs the formatter inside the disposable runner
image and then **fails on any `git diff`** (it never commits or pushes); `test` / `test-lib` / `check`
/ `build` are read-only. `actions/checkout` is pinned `@v5` (Node 24; `@v4` is the deprecated Node 20).

It is deliberately **not a build matrix**: the three subprojects have different gate sets and different
lean flags, so each job is written out. The flags (`USE_EMACS=0`, `USE_WASM=0`, sometimes `USE_WX=0` /
`USE_X_WINDOWS=0`) drop heavy **optional** image layers CI doesn't need — never a layer a gate needs
(see each job below).

## The jobs (what gates what)

Three axes the maintainer asked CI to cover — **format check**, **test**, **type-check** — across the
four languages (Python, Rust, C++, and the Tauri JavaScript). Mapped onto the subprojects:

### Python (`python/`) — the canonical implementation + behaviour oracle
- **`python-check-format`** — `make check-format USE_EMACS=0 USE_X_WINDOWS=0` (ruff format + ruff
  check, then fail on diff).
- **`python-type-check`** — `make type-check USE_EMACS=0` (ty). **Keeps `USE_X_WINDOWS` on** so ty can
  resolve the wxPython-importing GUI modules.
- **`python-test`** — `make test USE_EMACS=0` (pytest incl. `--doctest-modules`). Keeps `USE_X_WINDOWS`
  on: `--doctest-modules` imports every `src` module and the wx GUI front-ends `import wx` at module
  top (needs the GTK/X11 libs).

### Rust (`rust/`) — a Cargo workspace mirroring the Python
- **`rust-check-format`** — `make check-format USE_EMACS=0 USE_WASM=0` (rustfmt; also `deno fmt` over
  the Tauri frontend, via `format.sh`).
- **`rust-type-check`** — `make type-check USE_EMACS=0 USE_WASM=0`. **This is where the project's
  JavaScript is gated**: `make type-check` runs Deno over the Tauri frontend (`deno check --check-js` +
  `deno lint` + `deno fmt --check`), i.e. the JS format-check **and** type-check in one job (JSDoc +
  `checkJs`, no `node_modules`).
- **`rust-check`** — `make check USE_EMACS=0 USE_WASM=0` (`cargo check --workspace --all-targets`):
  compiles every workspace crate **including the wxDragon GUI (`hanoi-gui`)** and all test targets. The
  slow job — wxDragon's `build.rs` builds wxWidgets from source — but it is what gates GUI-crate
  compilation. (`hanoi-egui` and `tauri/` are separate workspaces, so `--workspace` doesn't pull them
  in; their compilation is not gated here — see "Known gaps".)
- **`rust-test`** — `make test-lib USE_EMACS=0 USE_WASM=0` (`cargo test -p hanoigame`): the shared
  crate's unit tests + doctests, without rebuilding wxWidgets (GUI compilation is covered by
  `rust-check`).

### C++ (`cpp/`) — two GUIs over the header-only engine
- **`cpp-check-format`** — `make check-format USE_EMACS=0 USE_WASM=0 USE_WX=0` (clang-format, fail on
  diff).
- **`cpp-build`** — `make build USE_EMACS=0 USE_WASM=0` (compiles the ImGui GUI + the wxWidgets GUI +
  the test runner). **Keeps `USE_WX`** so `hanoi-wx` compiles. **There is no separate C++ type-check
  job — the C++ compiler IS the type check**, so `build` is it.
- **`cpp-test`** — `make test USE_EMACS=0 USE_WASM=0 USE_WX=0` (the inline doctest `TEST_CASE`s, built
  into `hanoi-tests` and run under `ctest`).

## Coverage matrix

| Language          | format check            | test                         | type-check                         |
|-------------------|-------------------------|------------------------------|------------------------------------|
| Python            | `python-check-format`   | `python-test` (pytest+dt)    | `python-type-check` (ty)           |
| Rust              | `rust-check-format`     | `rust-test` (`test-lib`) + `rust-check` (compile all) | — (compiler, via `rust-check`) |
| C++               | `cpp-check-format`      | `cpp-test` (ctest/doctest)   | — (compiler, via `cpp-build`)      |
| JavaScript (Tauri)| in `rust-type-check` (`deno fmt --check`) | — (no JS test suite; see gaps) | in `rust-type-check` (`deno check --check-js`) |

## Known gaps (deliberate, noted for the next CI change)

- **No JavaScript `test` job** — the Tauri frontend has no JS test suite, only `deno check`/`lint`/`fmt`
  (all run by `rust-type-check`). Adding a JS "test" stage would require first writing JS tests.
- **`hanoi-egui` and `tauri/` (both separate Cargo workspaces) are not compile-gated** — `rust-check`'s
  `--workspace` does not reach them. The Tauri *frontend* JS is gated (deno); the Tauri *backend* crate
  and the egui crate are not built in CI.

## Related

- `.github/workflows/checks.yml` — the workflow this documents.
- `tasks/reference/per-language-subproject-layout.md` — the per-language `make` targets CI wraps.
- `tasks/archive/2026/10/27/github-actions-format-test-typecheck-ci.md` — the task that built it.
- `~/.claude/reference/javascript-coding-standard.md` — the Deno gate behind the JS checks.
