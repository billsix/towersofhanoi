#!/usr/bin/env bash
#
# 04-install-emacs.sh -- Emacs (the maintainer's editor) + its GTK/pgtk builds, plus the
# lsp-pyright backend (nodejs/npm + the pyright language server). Its own package group,
# gated by the Dockerfile's USE_EMACS ARG (the Makefile builds it in on a host and skips it
# in a lean nested image). No options -- see 01-install-base.sh for the design.
# Host-runnable: on a bare Fedora host, run this to add Emacs.
#
# The emacs PACKAGES (elpa) are NOT installed here -- they are vendored in the repo
# (entrypoint/dotfiles/.emacs.d/elpa, refreshed by `make update-emacs-packages`) and
# bind-mounted at `make shell`, so no MELPA download+compile runs during an image build.
#
# Two installers (dnf + npm), so accumulate: run both, report both, fail if either failed.
set -uo pipefail
s=0
dnf install -y emacs emacs-gtk+x11 emacs-pgtk nodejs npm || s=1
npm install -g pyright || s=1
exit $s
