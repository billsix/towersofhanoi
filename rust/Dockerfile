FROM registry.fedoraproject.org/fedora:45

# The Rust subproject of hanoi (github.com/billsix/towersofhanoi): a Cargo workspace
# reimplementing the Python canonical source feature-for-feature, with four front-ends
# over the shared `hanoigame` crate -- hanoi-cli, hanoi (ratatui TUI), hanoi-gui
# (wxDragon), and tauri/ (a Tauri v2 desktop app; just another UI, like the wx one).
# Self-contained: own image, own Makefile, own emacs set.

# USE_EMACS installs emacs + the vendored Rust dev set (rust-mode + rust-analyzer via
# lsp-mode). Makefile defaults it to 1; a bare `podman build` stays lean (0); a lean
# MINIMAL_IMAGE build drops it.
ARG USE_EMACS=0

# USE_WASM bakes the WebAssembly toolchain (wasm32 Rust std + trunk, both Fedora rpms,
# plus the matching wasm-bindgen CLI into trunk's cache) for the egui web build
# (make egui-web/egui-serve). Makefile defaults it to 1; a bare build stays lean (0); a
# lean MINIMAL_IMAGE build drops it. See entrypoint/03-install-wasm.sh.
ARG USE_WASM=0
# The wasm-bindgen CLI version trunk needs -- MUST match hanoi-egui/Cargo.lock's
# wasm-bindgen crate (the Makefile reads it from the lock and passes it here).
ARG WASM_BINDGEN_VERSION=0.2.129

# Deno version for the JS type-check gate (entrypoint/02-install-deno.sh). A pinned,
# checksum-verified binary baked at build so `make type-check` runs offline.
ARG DENO_VERSION=v2.9.8

# System-package installation lives in per-group scripts (entrypoint/0N-install-*.sh),
# host-runnable with no container runtime. The dnf cache mount + keepcache stay in the
# Dockerfile. 01-install-rust-base.sh installs the toolchain + native build stack.
COPY entrypoint/01-install-rust-base.sh /usr/local/bin/
COPY entrypoint/02-install-deno.sh /usr/local/bin/
COPY entrypoint/03-install-wasm.sh /usr/local/bin/
COPY entrypoint/04-install-emacs.sh /usr/local/bin/

RUN  --mount=type=cache,target=/var/cache/libdnf5 \
     --mount=type=cache,target=/var/lib/dnf \
     echo "keepcache=True" >> /etc/dnf/dnf.conf && \
     dnf upgrade -y && \
     /usr/local/bin/01-install-rust-base.sh && \
     echo "cargo run -q -p hanoi-cli" >> ~/.bash_history

# emacs BINARY only (USE_EMACS). The dev PACKAGES are NOT compiled into the image: like
# github.com/billsix/modelviewprojection and github.com/billsix/geometricalgebra, they are
# vendored in the repo (entrypoint/dotfiles/.emacs.d/elpa, source-only, refreshed by
# `make update-emacs-packages`) and bind-mounted at `make shell` via the Makefile's ELPA_MOUNT
# -- so no slow MELPA download+compile ever runs during an image build, and package/config
# edits are live without a rebuild. emacs only runs under `make shell` (which always supplies
# that mount); the front-end run targets never start it. Deliberate exception to "bake every
# dependency into the image": emacs is a dev convenience, not the product, and this image is
# not pushed for standalone pull. The rust-analyzer LSP backend is in 01-install-rust-base.sh.
RUN  --mount=type=cache,target=/var/cache/libdnf5 \
     --mount=type=cache,target=/var/lib/dnf \
     if [ "$USE_EMACS" = "1" ]; then /usr/local/bin/04-install-emacs.sh; fi

# WASM toolchain LAST of the dnf layers: its cache key includes WASM_BINDGEN_VERSION (read
# from hanoi-egui/Cargo.lock), so a bump rebuilds only this layer, not emacs or the base.
# See entrypoint/03-install-wasm.sh.
RUN  --mount=type=cache,target=/var/cache/libdnf5 \
     --mount=type=cache,target=/var/lib/dnf \
     if [ "$USE_WASM" = "1" ]; then WASM_BINDGEN_VERSION="$WASM_BINDGEN_VERSION" /usr/local/bin/03-install-wasm.sh ; fi

# Deno for the JS type-check gate (own RUN, source-independent, so it caches across
# frontend edits). See entrypoint/02-install-deno.sh.
RUN DENO_VERSION="$DENO_VERSION" /usr/local/bin/02-install-deno.sh

COPY entrypoint/.bashrc /root/
COPY entrypoint/shell.sh /usr/local/bin/shell.sh
COPY entrypoint/entrypoint.sh /entrypoint.sh
COPY entrypoint/format.sh /format.sh
# Bake the emacs config (init.el + helm.el + preferences.el). The config is baked, not mounted:
# `make shell` bind-mounts only the vendored elpa/ over /root/.emacs.d/elpa (the Makefile's
# ELPA_MOUNT), so package refreshes are live while config edits need a rebuild -- matching
# modelviewprojection/geometricalgebra. A no-mount emacs has the config but no packages, which is
# acceptable since emacs is only ever launched under `make shell`.
COPY entrypoint/dotfiles/.emacs.d/init.el entrypoint/dotfiles/.emacs.d/helm.el entrypoint/dotfiles/.emacs.d/preferences.el /root/.emacs.d/

# Bake the subproject's own source LATE, at the SAME path the bind-mount uses, so a
# pulled image has the code while `make shell` overrides it via the live mount at
# /hanoi-rust. NOTE: the crates are NOT cargo-built at image time -- wxDragon fetches +
# builds wxWidgets over the network at cargo-build time (see 01-install-rust-base.sh),
# so the build happens at runtime, cached in .container-target on the mount.
COPY . /hanoi-rust

# The interactive prompt / aliases / exit-format hook live in entrypoint/.bashrc (COPY'd
# above and bind-mounted by `make shell` so edits are live). No PS1 override here.

ENTRYPOINT ["/entrypoint.sh"]
