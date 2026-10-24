# Split hanoi into self-contained per-language subprojects (own Dockerfile + Makefile + emacs)

**Status:** done — ready to archive (python + rust subprojects built, tested, and GUI-verified; root
reduced to the book/umbrella; CLAUDE.md + a reference doc written). One optional follow-up remains (the
full `make docs` book build, unchanged by the split).
**Priority:** 5 **Difficulty:** 6
**Created:** 2026-10-24 (William Emerison Six <billsix@gmail.com>). Requested: "move python one to own
folder with own dockerfile makefile, same for rust one, same for any language. update CLAUDE.md to
reflect that. For each of them, make their own set of emacs packages, inspired by [the maintainer's
per-language emacs-config repo] … Just use it as inspiration."

## BLUF

hanoi previously built every language from **one** root `Dockerfile` + `Makefile`. The split made the
Python and Rust (incl. Tauri) implementations **self-contained subprojects** — each with its own image,
`Makefile`, `entrypoint/`, and a language-tailored emacs set — and reduced the root to the book +
workbook + bash + umbrella. The durable, reusable structure (the recipe for adding a language, incl.
the emacs/LSP setup) is in **`tasks/reference/per-language-subproject-layout.md`**; this doc is the work
record.

## What was done

- **`python/` subproject** — own `Dockerfile`/`Makefile`/`entrypoint/` (shell, entrypoint, format,
  type-check + `01-install-base.sh`, `03-install-xwindows.sh`), a Python emacs set (`.emacs.d/`:
  lsp-mode + pyright), `.dockerignore`, `.gitignore`, `CLAUDE.md`. Mounts at `/hanoi-python`; bakes its
  source + deps and re-installs editable from the mount at runtime. Run: `cd python && make
  cli | tui | wx | format | type-check`.
- **`rust/` subproject** — own build + a Rust emacs set (rust-mode + rust-analyzer; `rust-analyzer` was
  added to the toolchain, which the old root install lacked), `.dockerignore`, `CLAUDE.md`. Mounts at
  `/hanoi-rust`; crates build at runtime (cargo caches on the mount). **Tauri moved under `rust/`** via
  `git mv tauri rust/tauri`. Run: `cd rust && make cli | tui | wx | tauri | format`.
- **Root reduced** to the book/umbrella: the `Dockerfile` dropped `USE_RUST`/`USE_X_WINDOWS` (base +
  docs only); the `Makefile` dropped the per-language run targets, kept `docs`, and delegates
  `format`/`type-check` to `python/` + prints an umbrella banner; the now-dead
  `entrypoint/{03-install-xwindows,04-install-rust}.sh` were `git rm`'d. `CLAUDE.md` rewritten for the
  new layout.

## Decisions (maintainer, 2026-10-24)

- **Tauri lives inside `rust/`** as another UI target (like the wxDragon `hanoi-gui`), reusing the
  `hanoigame` crate — not a separate subproject, not left on the root.
- Remaining open questions were resolved with the recommended answers (maintainer said "start"): the
  book/`workbook` stay as root targets with the root as the umbrella; each subproject keeps its own
  `entrypoint/` (the duplication is the price of self-containment); this task converted only python +
  rust — the C++ task (`tasks/port-to-cpp-imgui-native-and-wasm.md`) creates `cpp/` itself.

## Issues found and fixed during the split

- **`test_byhand_drift.py` coupling** — it reaches up to the root's `tools/` + `docs/` (it's a
  book-drift guard, not a hanoigame unit test), which aren't in the isolated Python image, so it now
  **skips** when they're unreachable (still runs from the full checkout / root book gate / host).
- **Tauri + cargo workspace** — moving `tauri/` under `rust/` made cargo try to fold it into the rust
  workspace; fixed with an empty `[workspace]` table in the Tauri manifest (its own workspace root). Its
  path-dep became `hanoigame = { path = "../../hanoigame" }`.
- **Bare `>` prompt** — the subprojects had inherited the old root's `RUN echo "export PS1='>'"`; removed
  it, put a real prompt + `ls` color + the exit-format hook in each `entrypoint/.bashrc`, and bind-mount
  `.bashrc` so it's live.
- **Emacs/LSP polish** (per maintainer feedback): pinned the LSP project root to each subproject's
  mount, added the build/cache dirs to `lsp-file-watch-ignored-directories` (no more "watch N files?"
  prompt), enabled yasnippet (so `${1:arg}$0` completion snippets expand instead of inserting raw text),
  and baked `init.el`+`preferences.el` into both images. All captured as the reusable recipe in the
  reference doc.

## Verification (nested podman, 2026-10-24)

- **python:** lean + full images build; **128 pytest pass / 2 skip**; emacs + pyright present; MELPA
  packages install at build; baked `.emacs.d` loads lsp-mode/yasnippet/lsp-pyright without a mount.
  Maintainer confirmed `make wx` runs on the host.
- **rust:** image builds; **51 workspace tests pass**; both manifests `cargo verify-project` OK; the
  **wxDragon GUI crate builds** (wxWidgets compiled from source) and the **Tauri crate builds** (webkit
  linked, against the moved path-dep); baked `.emacs.d` loads lsp-mode/yasnippet/rust-mode without a
  mount. Maintainer confirmed `make wx` **and** `make tauri` run on the host.
- **root:** the reduced book image builds.

## Remaining (optional, not blocking)

- Full **book** build (`make docs`, `BUILD_DOCS=1`) — a long TeX build; unchanged by the split and
  proven to build at the image level.

## Related

- Reusable recipe: `tasks/reference/per-language-subproject-layout.md`.
- Sibling: `tasks/port-to-cpp-imgui-native-and-wasm.md` (the C++ port lands as `cpp/` in this layout).
- `tasks/reference/architecture-overview.md`; the per-subproject `python/CLAUDE.md` + `rust/CLAUDE.md`.
