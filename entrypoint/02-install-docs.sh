#!/usr/bin/env bash
#
# 02-install-docs.sh -- the book/docs toolchain (Sphinx + TeX Live). Corresponds to the
# Dockerfile's BUILD_DOCS flag; the Dockerfile runs this only when BUILD_DOCS=1. No
# options -- see 01-install-base.sh for the design.
#
# Single dnf call, so its own exit status is this script's exit status.
set -uo pipefail

dnf install -y \
    aspell \
    aspell-en \
    latexmk \
    make \
    mathjax \
    mathjax-main-fonts \
    mathjax-math-fonts \
    python3-furo \
    python3-sphinx-latex \
    python3-sphinx_rtd_theme \
    texlive \
    texlive-anyfontsize \
    texlive-dvipng \
    texlive-dvisvgm \
    texlive-standalone
