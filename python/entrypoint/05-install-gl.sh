#!/usr/bin/env bash
#
# 05-install-gl.sh -- OpenGL for the 3D front-end (hanoi-gl): GLFW, the Mesa GL/EGL
# libraries and drivers (llvmpipe software rendering when no GPU is passed through),
# and the X11/Wayland libraries GLFW loads with dlopen.
#
# One package group per script, no options: the Dockerfile runs it inside the
# USE_X_WINDOWS block (a GL window needs the display libraries too). The same script
# installs the same packages during `podman build`, on a bare Fedora host, or in a guest
# with no container runtime. Run 01-install-base.sh first. The list matches
# github.com/billsix/geometricalgebra's entrypoint/07-install-gl.sh.
#
# Single dnf call, so its own exit status is the gate.
set -uo pipefail

if ! command -v dnf >/dev/null 2>&1; then
    echo "05-install-gl.sh: needs 'dnf' (this installs Fedora packages), not found." >&2
    echo "Run on a Fedora host/guest, or inside the project's Fedora-based image." >&2
    exit 1
fi

dnf install -y glfw \
               mesa-dri-drivers \
               mesa-libEGL \
               mesa-libGL \
               libwayland-client \
               libwayland-cursor \
               libwayland-egl \
               libxkbcommon \
               libX11 \
               libXcursor \
               libXi \
               libXinerama \
               libXrandr
