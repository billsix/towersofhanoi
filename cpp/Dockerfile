FROM registry.fedoraproject.org/fedora:44

# The C++ subproject of hanoi: a Dear ImGui GUI over the hanoigame engine, building both a
# native desktop binary (`make gui`) and WebAssembly (`make webassembly`). Self-contained:
# own image, own Makefile, own emacs set. Recipe: tasks/reference/imgui-cpp-native-and-wasm.md.

# USE_EMACS installs emacs + the C/C++ dev set (lsp-mode + clangd). Default 1 in the Makefile.
ARG USE_EMACS=0
# USE_WASM installs the Emscripten SDK (needed only for `make webassembly`; ~1-1.5 GB). The
# Makefile defaults it to 1; a lean MINIMAL_IMAGE build drops it (native-only image).
ARG USE_WASM=0
# USE_WX installs the wxWidgets/wxGTK stack for the `make wx` front-end. Default 1 in the
# Makefile; a lean MINIMAL_IMAGE build drops it (the ImGui target doesn't need it).
ARG USE_WX=0
# The pinned Emscripten SDK version (reproducible; bump deliberately).
ARG EMSDK_VERSION=3.1.74

COPY entrypoint/01-install-cpp-base.sh entrypoint/02-install-emsdk.sh entrypoint/03-install-wx.sh /usr/local/bin/
COPY entrypoint/dotfiles/.emacs.d/install-melpa-packages.el /root/.emacs.d/install-melpa-packages.el

RUN  --mount=type=cache,target=/var/cache/libdnf5 \
     --mount=type=cache,target=/var/lib/dnf \
     echo "keepcache=True" >> /etc/dnf/dnf.conf && \
     dnf upgrade -y && \
     /usr/local/bin/01-install-cpp-base.sh && \
     if [ "$USE_WX" = "1" ]; then /usr/local/bin/03-install-wx.sh ; fi && \
     if [ "$USE_EMACS" = "1" ]; then \
       dnf install -y emacs && \
       emacs --batch --load /root/.emacs.d/install-melpa-packages.el ; \
     fi && \
     echo "make gui" >> ~/.bash_history

# emsdk in its own layer (heavy; caches independently of the dnf layer). The script reads
# the pinned version from the env. Skipped when USE_WASM=0 (a native-only / lean image).
RUN if [ "$USE_WASM" = "1" ]; then EMSDK_VERSION="$EMSDK_VERSION" /usr/local/bin/02-install-emsdk.sh; fi

COPY entrypoint/.bashrc /root/
COPY entrypoint/shell.sh /usr/local/bin/shell.sh
COPY entrypoint/entrypoint.sh /entrypoint.sh
COPY entrypoint/format.sh /format.sh
# Bake the emacs config (init.el + preferences.el) after the package layer so editing it
# doesn't bust the cache; `make shell` still bind-mounts the live .emacs.d over it.
COPY entrypoint/dotfiles/.emacs.d/init.el entrypoint/dotfiles/.emacs.d/preferences.el /root/.emacs.d/

# Bake the source LATE at the mount path. The native binary is built at runtime from the
# bind-mount (quick, propagates host edits), not here.
# NOTE on the shared XRC: hanoi.xrc is a git-tracked symlink -> ../ui/hanoi.xrc (the one true
# file is ui/hanoi.xrc at the repo root). The build context is this cpp/ dir, so the baked
# symlink dangles; at runtime the Makefile mounts the repo-root ui/ at /ui, so the wx app
# loads /ui/hanoi.xrc (the symlink resolves there). That mount IS the XRC delivery mechanism:
# these images are DEVELOPMENT-ONLY and never pushed to a registry, so there is no mount-less
# pulled-image case to bake a resolved copy for. See
# tasks/cpp-add-wx-frontend-and-recipe-view-parity.md Decision 1.
COPY . /hanoi-cpp

# Pre-warm the Emscripten cache (the SDL2 port + the system libraries emcc builds on first
# use) at IMAGE-BUILD time, so a later `make serve` / `make webassembly` in an ephemeral
# --rm container reuses the baked cache under /opt/emsdk/.../cache instead of
# re-downloading/rebuilding it every run. A throwaway build of the project with the real
# wasm flags warms exactly what's needed; its output is discarded (the cache stays in the
# image layer). Same spirit as the dnf keepcache idiom, for the emscripten toolchain.
RUN if [ "$USE_WASM" = "1" ]; then \
      bash -c '. /opt/emsdk/emsdk_env.sh && cd /hanoi-cpp && \
               emcmake cmake -S . -B /tmp/warm -DCMAKE_BUILD_TYPE=Release && \
               cmake --build /tmp/warm && rm -rf /tmp/warm /hanoi-cpp/web' ; \
    fi

ENTRYPOINT ["/entrypoint.sh"]
