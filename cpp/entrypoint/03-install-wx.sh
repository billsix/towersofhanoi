#!/usr/bin/env bash
#
# 03-install-wx.sh -- the wxWidgets (wxGTK) dev stack for the C++ `make wx` front-end.
# wxGTK-devel provides wx-config + the wxWidgets libraries, including the XRC runtime
# (wxXmlResource) the GUI loads the shared hanoi.xrc with; libSM-devel/libICE-devel are
# the X11 session-management libs wxWidgets links against. This is the C++ sibling of the
# Python subproject's USE_X_WINDOWS GTK stack. Dispatched by the Dockerfile's USE_WX ARG;
# the native ImGui build (SDL2/GL from 01-install-cpp-base.sh) is independent of it.
#
# One package group per script, no options (which groups install is the Dockerfile's
# ARG decision). A single dnf call, so its own exit status is the gate.
set -uo pipefail

if ! command -v dnf >/dev/null 2>&1; then
    echo "03-install-wx.sh: needs 'dnf' (this installs Fedora packages), not found." >&2
    echo "Run on a Fedora host/guest, or inside the project's Fedora-based image." >&2
    exit 1
fi

dnf install -y wxGTK-devel \
               libSM-devel \
               libICE-devel
