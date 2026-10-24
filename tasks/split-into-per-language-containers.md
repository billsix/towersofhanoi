# Split hanoi into self-contained per-language subprojects (own Dockerfile + Makefile + emacs)

**Status:** proposed — needs go-ahead
**Priority:** 5 **Difficulty:** 6
**Created:** 2026-10-24 (William Emerison Six <billsix@gmail.com>). Requested: "move python one to own
folder with own dockerfile makefile, same for rust one, same for any language. update CLAUDE.md to
reflect that. For each of them, make their own set of emacs packages, inspired by [the maintainer's
per-language emacs-config repo]. This is not a public repo, so no need to reference it at all, that
would be confusing. Just use it as inspiration for your work."

## BLUF

hanoi (github.com/billsix/towersofhanoi) today builds **every language from one root `Dockerfile` +
one root `Makefile`**; the Python, Rust, and Tauri sources already sit in `python/`, `rust/`, `tauri/`
but share that single image and driver. This task makes each language folder a **self-contained
subproject** with its **own `Dockerfile`, `Makefile`, `entrypoint/`, and a language-tailored emacs
package set** (so a contributor can `cd python && make shell` or `cd rust && make shell` and get only
that toolchain), and updates `CLAUDE.md` to describe the new layout. "Done" = each language subproject
builds and runs its front-ends on its own, the root keeps only what is genuinely cross-language
(the book, the workbook, an umbrella), and `CLAUDE.md` reflects it. **Do not delete the Python-as-
behaviour-oracle relationship** — isolation is about build/tooling, not about severing the shared
teaching model.

## Context (read first)

- **Read first:** `/foo/opt/hanoi/CLAUDE.md` (project framing + current layout, lines ~38-78),
  `/foo/opt/hanoi/Makefile` (the root orchestrator — per-language dispatch macros at lines ~146-185),
  `/foo/opt/hanoi/Dockerfile` (ARG-gated installs, lines ~20-27), and the entrypoint scripts under
  `/foo/opt/hanoi/entrypoint/`.
- **Current state (verified 2026-10-24):**
  - **One** real `Dockerfile` (root) and **one** hand-written root `Makefile` serve all languages;
    `docs/Makefile` and `workbook/Makefile` are the only other Makefiles. `python/` and `rust/` have
    **no** Dockerfile/Makefile of their own.
  - The root `Makefile` dispatches per language via setup macros: `PYTHON_SETUP` (`uv pip install -e .`
    → targets `python-cli`/`python-tui`/`python-wx`), `RUST_SETUP` (cargo target/home redirect →
    `rust-cli`/`rust-tui`/`rust-wx`), `TAURI_SETUP` (→ `rust-tauri`). Shared `SHELL_RUN_FLAGS` feeds
    `shell`/`shell-exec`; `PODMAN_RUN_FLAGS` is the nested-podman passthrough; X11/Wayland mounts via
    `PLAY_FLAGS`.
  - The Dockerfile gates toolchains by build ARG (`BUILD_DOCS`, `USE_X_WINDOWS`, `USE_RUST`) and
    factors installs into `entrypoint/0N-install-*.sh`: `01-install-base.sh` (Python, **no** C/C++
    compiler), `02-install-docs.sh` (Sphinx/TeX), `03-install-xwindows.sh` (X11/Wayland, **no**
    OpenGL/mesa), `04-install-rust.sh` (Rust toolchain **plus** gcc/g++/clang/cmake/ninja for
    wxDragon + webkit2gtk for Tauri).
  - **Sources already in folders:** `python/` (canonical setuptools package `python/src/hanoigame/`:
    `hanoimodel.py`, `commands.py`, `engine.py`, `presenter.py`, `recipe.py`, `board_renderers.py` +
    front-ends `hanoicli.py`/`hanoigame.py`/`hanoigui.py`); `rust/` (Cargo workspace: library crate
    `rust/hanoigame/` + binaries `hanoi-cli`/`hanoi`/`hanoi-gui`); `tauri/` (a 4th front-end over the
    same `hanoigame` Rust crate — note it depends on the `rust/` crate, so it is **not** independent of
    `rust/`).
  - **No emacs/dotfiles anywhere today** — this part is greenfield.
- **The model to imitate (inspiration only — do NOT name or link the source repo in any committed
  file):** the maintainer keeps a private repo that is organized as **one folder per language**, each a
  complete container-per-language subproject: `Dockerfile`, `Makefile`, `entrypoint/{shell.sh,
  entrypoint.sh,format.sh}`, `output/.keep`, `CLAUDE.md`, and
  `entrypoint/dotfiles/.emacs.d/{init.el,preferences.el,elpa/<vendored packages>}`. The emacs set is
  tailored per language (e.g. magit + lsp-mode + flycheck + the language major-mode and its
  language-server glue). Reproduce that **shape** for hanoi's languages from scratch; write hanoi's own
  emacs configs — do not copy that repo or reference it.
- **Conventions that bind this work:** the container-per-project template and the "Self-contained
  images + live source" rule in the maintainer's personal overlay — each subproject's image must bake
  its third-party deps into committed layers (offline-rebuildable) and rebuild only its own source from
  the bind-mount at runtime. Each subproject's `Makefile` keeps the standard contract: `help`/`image`/
  `shell`/`shell-exec` (sharing one `SHELL_RUN_FLAGS`), `format`, `type-check` (Python), `image-export`/
  `image-import`, `PODMAN_RUN_FLAGS` on every `run` line (never `build`), `CONTAINER_NAME` per
  subproject, repo mounted at its own path.

## Plan (sketch — refine once the open questions are answered)

1. **`python/`** → add `python/Dockerfile`, `python/Makefile`, `python/entrypoint/{shell.sh,
   entrypoint.sh,format.sh,type-check.sh,01-install-base.sh,03-install-xwindows.sh}`, and
   `python/entrypoint/dotfiles/.emacs.d/` with a Python-tailored emacs set (python-mode/eglot or
   lsp-mode + a Python language server, ruff/flycheck, magit). Targets: `python-cli`/`-tui`/`-wx` become
   plain `cli`/`tui`/`wx` (or `run-*`) inside the subproject. Carry the X11/Wayland passthrough for the
   wxPython GUI.
2. **`rust/`** → `rust/Dockerfile`, `rust/Makefile`, `rust/entrypoint/*`, Rust-tailored emacs set
   (rust-mode/rustic + rust-analyzer via eglot/lsp-mode, cargo integration, magit). Carry the native
   C/C++/cmake/ninja + wxGTK stack the wxDragon GUI needs **plus webkit2gtk** for Tauri. **Tauri lives
   inside the `rust/` subproject as just another UI target** (like `hanoi-gui`/wxDragon) — decided
   2026-10-24; it already builds over the same `hanoigame` crate. So the rust subproject's Makefile
   exposes the cli/tui/wx/tauri run targets.
3. **Root** → reduce the root `Makefile`/`Dockerfile` to only what is cross-language: the Sphinx book
   (`docs/`), the workbook, the bash demos, and an **umbrella** `help`/target that can invoke each
   subproject (or just document "cd into a language and `make`"). Keep the Python-as-oracle relationship
   documented.
4. **`CLAUDE.md`** → rewrite the layout/build sections to describe per-language subprojects, how to
   build/run each, and the emacs-per-language convention.
5. **Verify** each subproject nested: `make image` + run a front-end (headless where possible), `make
   format`/`type-check` green, and the offline export/import test per the self-contained-images rule.

## Decisions (maintainer, 2026-10-24)

- **Tauri lives inside the `rust/` subproject** as another UI target, like the wxDragon `hanoi-gui` — it
  is just another front-end over the `hanoigame` crate. Not a separate subproject; not left on the root.

## Open questions

1. **What stays at the root.** Should the book (`docs/`) and `workbook/` each also become their own
   container subproject (matching the template), or stay as root-level `make docs`/`make workbook`
   targets? Recommend: keep docs/workbook as root targets (they're not a "language"), and make the root
   an umbrella that documents the per-language subprojects.
2. **Shared vs duplicated entrypoint logic.** Each subproject gets its own `entrypoint/`, which
   duplicates boilerplate (shell.sh skeleton, PODMAN_RUN_FLAGS). Accept the duplication (matches the
   template — each subproject is self-contained), or factor a shared snippet? Recommend: accept
   duplication; self-containment is the point.
3. **"Same for any language" — scope now.** Only Python, Rust (+Tauri) exist today; the C++ port is a
   separate task (`tasks/port-to-cpp-imgui-native-and-wasm.md`). Should this task pre-create an empty
   `cpp/` subproject skeleton, or should the C++ task create `cpp/` already in the per-language shape?
   Recommend: the C++ task creates `cpp/` directly in the new shape; this task only converts the
   existing python/rust.

## Related

- Sibling task: `tasks/port-to-cpp-imgui-native-and-wasm.md` (the C++ port lands as a new per-language
  subproject under this same layout).
- Existing Tauri tasks: `tasks/tauri-frontend-js-options.md`, `tasks/tauri-frontend-lint.md`.
- Reference: `tasks/reference/architecture-overview.md`, and the container-per-project template +
  "Self-contained images + live source" rules in the maintainer's conventions.
