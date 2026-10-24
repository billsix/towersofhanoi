FROM registry.fedoraproject.org/fedora:44

# The Rust subproject of hanoi (github.com/billsix/towersofhanoi): a Cargo workspace
# reimplementing the Python canonical source feature-for-feature, with four front-ends
# over the shared `hanoigame` crate -- hanoi-cli, hanoi (ratatui TUI), hanoi-gui
# (wxDragon), and tauri/ (a Tauri v2 desktop app; just another UI, like the wx one).
# Self-contained: own image, own Makefile, own emacs set.

# USE_EMACS installs emacs + the vendored Rust dev set (rust-mode + rust-analyzer via
# lsp-mode). Makefile defaults it to 1; a bare `podman build` stays lean (0); a lean
# MINIMAL_IMAGE build drops it.
ARG USE_EMACS=0

# System-package installation lives in per-group scripts (entrypoint/0N-install-*.sh),
# host-runnable with no container runtime. The dnf cache mount + keepcache stay in the
# Dockerfile. 01-install-rust-base.sh installs the toolchain + native build stack.
COPY entrypoint/01-install-rust-base.sh /usr/local/bin/
COPY entrypoint/dotfiles/.emacs.d/install-melpa-packages.el /root/.emacs.d/install-melpa-packages.el

RUN  --mount=type=cache,target=/var/cache/libdnf5 \
     --mount=type=cache,target=/var/lib/dnf \
     echo "keepcache=True" >> /etc/dnf/dnf.conf && \
     dnf upgrade -y && \
     /usr/local/bin/01-install-rust-base.sh && \
     if [ "$USE_EMACS" = "1" ]; then \
       dnf install -y emacs && \
       emacs --batch --load /root/.emacs.d/install-melpa-packages.el ; \
     fi && \
     echo "cargo run -q -p hanoi-cli" >> ~/.bash_history

COPY entrypoint/.bashrc /root/
COPY entrypoint/shell.sh /usr/local/bin/shell.sh
COPY entrypoint/entrypoint.sh /entrypoint.sh
COPY entrypoint/format.sh /format.sh
# Bake the emacs config (init.el + preferences.el) into the image so emacs works from the
# baked image even without the bind-mount (e.g. a pulled image). Placed AFTER the dnf +
# MELPA layer so editing init.el doesn't bust the package-install cache; the packages
# themselves are installed by the RUN above via install-melpa-packages.el. (`make shell`
# still bind-mounts the live .emacs.d over this, so edits remain live without a rebuild.)
COPY entrypoint/dotfiles/.emacs.d/init.el entrypoint/dotfiles/.emacs.d/preferences.el /root/.emacs.d/

# Bake the subproject's own source LATE, at the SAME path the bind-mount uses, so a
# pulled image has the code while `make shell` overrides it via the live mount at
# /hanoi-rust. NOTE: the crates are NOT cargo-built at image time -- wxDragon fetches +
# builds wxWidgets over the network at cargo-build time (see 01-install-rust-base.sh),
# so the build happens at runtime, cached in .container-target on the mount.
COPY . /hanoi-rust

# The interactive prompt / aliases / exit-format hook live in entrypoint/.bashrc (COPY'd
# above and bind-mounted by `make shell` so edits are live). No PS1 override here.

ENTRYPOINT ["/entrypoint.sh"]
