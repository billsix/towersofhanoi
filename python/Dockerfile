FROM registry.fedoraproject.org/fedora:44

# The Python subproject of hanoi (github.com/billsix/towersofhanoi): the hanoigame
# package and its three front-ends (hanoi-cli / hanoi / hanoi-gui). Self-contained --
# own image, own Makefile, own emacs set. The Sphinx book and workbook stay at the
# repo root (they are not a "language").

# USE_X_WINDOWS installs the X11/Wayland client libs (03-install-xwindows.sh) so the
# wxPython GUI (hanoi-gui) can open a window. Makefile defaults it to 1; a bare
# `podman build` stays lean (0). A lean MINIMAL_IMAGE build drops it.
ARG USE_X_WINDOWS=0
# USE_EMACS installs emacs + the vendored Python dev set (lsp-pyright over pyright).
# Makefile defaults it to 1; a bare `podman build` stays lean (0).
ARG USE_EMACS=0

# System-package installation lives in per-group scripts (entrypoint/0N-install-*.sh),
# host-runnable with no container runtime; the scripts take no options -- WHICH optional
# groups run is decided here by the ARG `if` blocks. The dnf cache mount + keepcache stay
# in the Dockerfile (build plumbing). 01-install-base.sh also does `dnf upgrade`.
COPY entrypoint/01-install-base.sh entrypoint/03-install-xwindows.sh /usr/local/bin/

RUN  --mount=type=cache,target=/var/cache/libdnf5 \
     --mount=type=cache,target=/var/lib/dnf \
     echo "keepcache=True" >> /etc/dnf/dnf.conf && \
     /usr/local/bin/01-install-base.sh && \
     echo "hanoi" >> ~/.bash_history

# emacs BINARY + the lsp-pyright backend (nodejs/npm/pyright) only. The emacs dev PACKAGES are
# NOT compiled into the image: like github.com/billsix/modelviewprojection and
# github.com/billsix/geometricalgebra, they are vendored in the repo
# (entrypoint/dotfiles/.emacs.d/elpa, source-only, refreshed by `make update-emacs-packages`)
# and bind-mounted at `make shell` via the Makefile's ELPA_MOUNT -- so no slow MELPA
# download+compile ever runs during an image build, and package/config edits are live without a
# rebuild. emacs only runs under `make shell` (which always supplies that mount). Deliberate
# exception to "bake every dependency into the image": emacs is a dev convenience, not shipped.
RUN  --mount=type=cache,target=/var/cache/libdnf5 \
     --mount=type=cache,target=/var/lib/dnf \
     --mount=type=cache,target=/root/.npm \
     if [ "$USE_EMACS" = "1" ]; then \
       dnf install -y emacs nodejs npm && \
       npm install -g pyright ; \
     fi

RUN  --mount=type=cache,target=/var/cache/libdnf5 \
     --mount=type=cache,target=/var/lib/dnf \
     if [ "$USE_X_WINDOWS" = "1" ]; then /usr/local/bin/03-install-xwindows.sh; fi

# Third-party Python deps: fetched + installed into a committed layer at build time
# (offline-rebuildable). wxPython comes from dnf (python3-wxpython4), so strip it from
# the pip set. Manifest COPY'd before the source so a source edit doesn't bust this layer.
COPY requirements.txt /requirements.txt
RUN  --mount=type=cache,target=/root/.cache/uv \
     uv pip install --system setuptools && \
     grep -v -i wxpython /requirements.txt > /requirements-nowx.txt && \
     uv pip install --system -r /requirements-nowx.txt && \
     rm /requirements.txt /requirements-nowx.txt

COPY entrypoint/.bashrc /root/
COPY entrypoint/shell.sh /usr/local/bin/shell.sh
COPY entrypoint/entrypoint.sh /entrypoint.sh
COPY entrypoint/format.sh /format.sh
COPY entrypoint/type-check.sh /type-check.sh
# Bake the emacs config (init.el + preferences.el) so the baked image has a usable config;
# `make shell` bind-mounts the live .emacs.d over this (config AND the vendored elpa), so
# edits stay live without a rebuild. The dev packages are mounted, not baked (see the emacs
# RUN above), so a no-mount emacs would have config but no packages -- acceptable here since
# emacs is only ever launched under `make shell`.
COPY entrypoint/dotfiles/.emacs.d/init.el entrypoint/dotfiles/.emacs.d/preferences.el /root/.emacs.d/

# Bake the subproject's own source LATE (after the dep layer) at the SAME path the
# bind-mount uses, and install it editable + offline -- so a pulled image runs
# standalone while `make shell` overrides it via the live mount at /hanoi-python.
COPY . /hanoi-python
RUN uv pip install --no-deps --no-index --no-build-isolation --system -e /hanoi-python

# The interactive prompt / aliases / exit-format hook live in entrypoint/.bashrc (COPY'd
# above and bind-mounted by `make shell` so edits are live). No PS1 override here.

ENTRYPOINT ["/entrypoint.sh"]
