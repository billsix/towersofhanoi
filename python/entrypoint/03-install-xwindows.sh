#!/usr/bin/env bash
#
# 03-install-xwindows.sh -- X11 / Wayland client libraries so the wxPython GUI
# (hanoi-gui) can open a window from the container.
#
# One package group per script, no options: which optional groups also get installed is
# decided by the Dockerfile's ARG `if` blocks (or by a human choosing which scripts to
# run). The same script installs the same packages during `podman build`, on a bare
# Fedora host, or in a guest with no container runtime. Run 01-install-base.sh first.
#
# hanoi-gui is wxPython/GTK with a 2D (wx.GraphicsContext / Cairo) board renderer -- it
# needs GTK plus the X11 and Wayland client libraries, but NO OpenGL. That is why this
# list omits the mesa GL drivers and glfw that a GL project would add here.
#
# Single dnf call, so its own exit status is the gate.
set -uo pipefail

if ! command -v dnf >/dev/null 2>&1; then
    echo "03-install-xwindows.sh: needs 'dnf' (this installs Fedora packages), not found." >&2
    echo "Run on a Fedora host/guest, or inside the project's Fedora-based image." >&2
    exit 1
fi

dnf install -y gtk3 \
               python3-wxpython4 \
               libX11 \
               libXext \
               libXrender \
               libXi \
               libXrandr \
               libXcursor \
               libXfixes \
               libXdamage \
               libXcomposite \
               libXinerama \
               libXtst \
               libwayland-client \
               libwayland-cursor \
               libxkbcommon
