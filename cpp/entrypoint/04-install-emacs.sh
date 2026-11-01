#!/usr/bin/env bash
#
# 04-install-emacs.sh -- Emacs (the maintainer's editor) + its GTK/pgtk builds. Its own
# package group, gated by the Dockerfile's USE_EMACS ARG (the Makefile builds it in on a
# host and skips it in a lean nested image). No options -- WHICH optional groups run is
# decided by the Dockerfile's `if` blocks; see 01-install-cpp-base.sh for the design.
# Host-runnable: on a bare Fedora host, run this to add Emacs.
#
# The C/C++ LSP backend (clangd) is installed by 01-install-cpp-base.sh with the rest of
# the toolchain, not here. The emacs PACKAGES (elpa) are NOT installed here either -- they
# are vendored in the repo (entrypoint/dotfiles/.emacs.d/elpa, refreshed by
# `make update-emacs-packages`) and bind-mounted at `make shell`, so no MELPA
# download+compile runs during an image build.
#
# Single dnf call, so its own exit status is this script's exit status.
set -uo pipefail

dnf install -y \
    emacs \
    emacs-gtk+x11 \
    emacs-pgtk
