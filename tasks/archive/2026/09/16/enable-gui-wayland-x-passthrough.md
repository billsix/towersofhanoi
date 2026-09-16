# Enable GUI display passthrough (Wayland/X) so `hanoi-gui` runs from the container

**Status:** complete
**Completed:** 2026-09-16 — implemented, committed ("enable gui in container"), verified headlessly via
Xvfb (X11 path), and confirmed by the maintainer on a live **Wayland** session.
**Priority:** 4
**Difficulty:** 4
**Started:** 2026-09-16

## What this was

`hanoi-gui` (wxPython) could not open a window from the container: the image installed the wx toolkit
(`python3-wxpython4` via dnf in `entrypoint/01-install-base.sh`, which pulls gtk3 + most libX* as RPM
deps), but the `Makefile` passed no display flags and there was no `USE_X_WINDOWS` build flag —
`CLAUDE.md` even said "the GUI needs X forwarding," yet the container never wired it up. The task added
the display passthrough the same way **modelviewprojection** (`github.com/billsix/modelviewprojection`)
does it, adapted to hanoi's wxPython/GTK **2D** GUI (not MVP's glfw/OpenGL demos), with the libraries
and flags on by default.

## What was decided, and why

Four questions the maintainer settled (2026-09-16):

- **`USE_X_WINDOWS ?= 1` — plain, on everywhere including nested builds.** This mirrors MVP's literal
  form ("the same way as it's done there"). It is a deliberate departure from the minimal-nested-image
  standard's "flip GUI extras off when nested" default (hanoi has no headless-Mesa gate — its gate is
  pytest); accepted for MVP parity and to keep the GUI usable from a nested shell.
- **Install the X libs explicitly**, in a new `entrypoint/03-install-xwindows.sh`, even though
  `python3-wxpython4` pulls most of them transitively — so the dependency is intentional, not incidental.
- **Trimmed library set**, because hanoi's GUI is wx/GTK 2D (Cairo), not OpenGL: dropped MVP's
  `mesa-dri-drivers`/`mesa-libGLU-devel` and glfw, and dropped the `PYGLFW_LIBRARY` env from the Wayland
  flags (glfw-only in MVP, meaningless here). Installed `gtk3`, the `libX*` interaction set, and
  `libwayland-client`/`libwayland-cursor`/`libxkbcommon` for the GTK Wayland backend. `DRI_DEVICE` was
  kept (harmless — it auto-skips when `/dev/dri` is absent).
- **Verification by the agent, headless via Xvfb** (X11 path); the real Wayland session was the
  maintainer's check on a live desktop.

## What was built

- `Makefile`: added `USE_X_WINDOWS ?= 1`, `X_FLAGS_FOR_CONTAINER` (DISPLAY + `/tmp/.X11-unix` + the
  SELinux `container_runtime_t` label), `DRI_DEVICE`, and `WAYLAND_FLAGS_FOR_CONTAINER` (the Wayland
  socket + `XDG_*` env, without `PYGLFW_LIBRARY`); threaded both flag sets into the shared
  `SHELL_RUN_FLAGS` so `shell` and `shell-exec` inherit them; and passed
  `--build-arg USE_X_WINDOWS=$(USE_X_WINDOWS)` on `image`. `format`/`type-check`/`docs` were untouched.
- `Dockerfile`: `ARG USE_X_WINDOWS=0` (bare build stays lean) + an `if [ "$USE_X_WINDOWS" = "1" ]`
  dispatch to the new script, COPY'd alongside 01/02.
- `entrypoint/03-install-xwindows.sh`: a guarded-`dnf` group script (no options, matching
  `01-install-base.sh`'s shape) installing the trimmed lib set above.
- `CLAUDE.md`: documented the flag, the passthrough, and how to run the GUI.

## Verification

Built with `USE_X_WINDOWS=1` (nested; also the default) and verified headlessly via Xvfb with a
one-shot proof harness (removed at archive; recoverable from git history): all libs present, wxPython
created an App+Frame, and `hanoi-gui` launched with no library/display error. The maintainer then
confirmed the GUI opens on a live Wayland session.
