# Enable GUI display passthrough (Wayland/X) so `hanoi-gui` runs from the container

**Status:** complete
**Completed:** 2026-09-16 — implemented, committed ("enable gui in container"), and verified headlessly
via Xvfb (X11 path). The maintainer then confirmed `hanoi-gui` on a live **Wayland** session works
(2026-09-16), closing the one owed follow-up from Q4. The one-shot Xvfb proof harness under
`tasks/adhoc/` was removed at archive (recoverable from history; it PASSED).
**Priority:** 4
**Difficulty:** 4
**Started:** 2026-09-16

## BLUF

`hanoi-gui` (wxPython) can't currently open a window from the container: the image installs the wx
toolkit but the `Makefile` passes no display flags and there's no `USE_X_WINDOWS` build flag. Mirror
the setup in **modelviewprojection** (`github.com/billsix/modelviewprojection`) — a `USE_X_WINDOWS`
flag defaulted on, an `entrypoint/03-install-xwindows.sh` group script for the X11/Wayland client
libraries, and `X_FLAGS_FOR_CONTAINER` + `WAYLAND_FLAGS_FOR_CONTAINER` threaded into the `shell`/
`shell-exec` run flags — adapted for hanoi's wxPython/GTK 2D GUI (**not** MVP's glfw/OpenGL demos).
Done = `make shell` on a host with a display lets `hanoi-gui` open its window under both X11 and
Wayland, with the libraries and flags on by default.

## Context — read first

- **hanoi's GUI today.** `hanoi-gui` is wxPython (XRC UI; text or `wx.GraphicsContext` **2D** board
  renderer — Cairo-based, **no OpenGL/glfw**). `CLAUDE.md` already says "the GUI needs X forwarding,"
  but the container never wired it up. The wx toolkit itself is installed: `python3-wxpython4` in
  `entrypoint/01-install-base.sh` (dnf), which pulls `gtk3` + most `libX*` as RPM dependencies
  transitively. `python/requirements.txt` also pins `wxPython==4.2.5` but the Dockerfile strips it
  from the pip layer (`grep -v -i wxpython`) — wx comes from dnf, not pip.
- **What hanoi lacks (the gap):**
  - `Makefile`: no `USE_X_WINDOWS` flag, no `X_FLAGS_FOR_CONTAINER`/`WAYLAND_FLAGS_FOR_CONTAINER`/
    `DRI_DEVICE`, and `SHELL_RUN_FLAGS` carries none of them (so `shell`/`shell-exec` start with no
    `DISPLAY`, no X socket, no Wayland socket).
  - `Dockerfile`: only `ARG BUILD_DOCS=0`; no `USE_X_WINDOWS` ARG and no dispatch to an X-libs script.
  - No `entrypoint/03-install-xwindows.sh`.
- **The template — modelviewprojection** (`github.com/billsix/modelviewprojection`; mounted in this
  sandbox alongside hanoi). Its container-GUI setup is what "the same way as it's done there" means.
  Read its `Makefile`, `Dockerfile`, and `entrypoint/03-install-xwindows.sh`. The relevant pieces are
  inlined below so this task is cold-executable.
- **Conventions that bear on this task:**
  - Project template (personal overlay): the GUI story is `USE_X` / X11 block + a
    `WAYLAND_FLAGS_FOR_CONTAINER` block; feature flags are `--build-arg`, default `1` in the Makefile
    and `0` in the Dockerfile ARG; every bind mount uses `:Z`; host-agnostic package installs live in
    `entrypoint/0N-install-<group>.sh` group scripts the Dockerfile dispatches by ARG `if`.
  - **Minimal-nested-image standard** (`~/.claude/reference/minimal-nested-images.md`): GUI/display
    extras (`USE_X_WINDOWS`) normally flip **off** when built nested (`NESTED_PODMAN=1`) *unless* the
    project runs headless verification on the image's own Mesa (as MVP does). hanoi has **no** headless
    GUI gate — its gate is pytest — so this is a live design decision (see Open questions Q1). hanoi
    just adopted this standard for `BUILD_DOCS` in `tasks/archive/2026/09/16/minimal-nested-image.md`.
  - Multi-`dnf` group scripts must accumulate exit status (`… || status=1; exit $status`), guard for
    `dnf` presence, and take no options — same shape as `entrypoint/01-install-base.sh`.

### What MVP does, exactly (the pattern to copy)

- `Makefile` flag: `USE_X_WINDOWS ?= 1`; `--build-arg USE_X_WINDOWS=$(USE_X_WINDOWS)` on `image`.
- `Makefile` display flags:
  ```make
  X_FLAGS_FOR_CONTAINER = -e DISPLAY=$(DISPLAY) \
      -v /tmp/.X11-unix:/tmp/.X11-unix \
      --security-opt label=type:container_runtime_t
  # GPU render node for hardware GL; skipped if /dev/dri is absent.
  DRI_DEVICE := $(shell [ -d /dev/dri ] && echo "--device /dev/dri")
  WAYLAND_FLAGS_FOR_CONTAINER = -e "XDG_SESSION_TYPE=wayland" \
      -e "WAYLAND_DISPLAY=${WAYLAND_DISPLAY}" \
      -e "XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR}" \
      -e "PYGLFW_LIBRARY=/usr/lib64/libglfw.so.3" \    # <- glfw-only; DROP for hanoi (see Notes)
      -v "${XDG_RUNTIME_DIR}:${XDG_RUNTIME_DIR}" \
      $(DRI_DEVICE)
  ```
  Both are appended to the shared `SHELL_RUN_FLAGS` block so `shell` and `shell-exec` inherit them.
- `Dockerfile`: `ARG USE_X_WINDOWS=0` + `if [ "$USE_X_WINDOWS" = "1" ]; then /usr/local/bin/03-install-xwindows.sh; fi`.
- `entrypoint/03-install-xwindows.sh` installs: `libXcomposite libXcursor libXdamage libXfixes libXft
  libXi libXinerama libXmu libXrandr libXrender libXres libXtst libXv libXxf86vm mesa-dri-drivers
  mesa-libGLU-devel libwayland-egl libwayland-client libxkbcommon`. (The `mesa-*` and glfw bits serve
  MVP's OpenGL demos — see Notes for what hanoi actually needs.)

## Goal

Let a maintainer run `hanoi-gui` from inside `make shell` on a real desktop, under both X11 and
Wayland, with the required libraries installed and the display flags applied **by default** — set up
the same way modelviewprojection does it, adapted to hanoi's wxPython/GTK 2D GUI.

## Plan

- [x] `Makefile`: added `USE_X_WINDOWS ?= 1` (plain, per Q1), `X_FLAGS_FOR_CONTAINER`, `DRI_DEVICE`,
      `WAYLAND_FLAGS_FOR_CONTAINER` (**without** `PYGLFW_LIBRARY`), and
      `--build-arg USE_X_WINDOWS=$(USE_X_WINDOWS)` on `image`. Both flag sets go into `SHELL_RUN_FLAGS`
      (shared by `shell` + `shell-exec`); `format`/`type-check`/`docs` untouched.
- [x] `Dockerfile`: `ARG USE_X_WINDOWS=0` + the `if [ "$USE_X_WINDOWS" = "1" ]` dispatch to the new
      script (COPY'd alongside 01/02); breadcrumb comment kept.
- [x] `entrypoint/03-install-xwindows.sh`: guarded-`dnf` group script with the trimmed GTK/X11/Wayland
      client-lib set (per Q3 — no mesa GL, no glfw). Executable bit set.
- [x] Built with `USE_X_WINDOWS=1` (nested; also the default) and verified headlessly via Xvfb (Q4)
      with a one-shot proof harness (removed at archive; recoverable from git history): all libs
      present, wxPython creates an App+Frame, `hanoi-gui` launches with no library/display error. **PASS.**
- [x] Updated `CLAUDE.md` (build/container section: the flag, the passthrough, run instructions).
      Staged all touched files.

## Notes / decisions

- **hanoi is wx/GTK 2D, not glfw/OpenGL.** Copy the X/Wayland *passthrough* verbatim, but:
  - **Drop `PYGLFW_LIBRARY`** from `WAYLAND_FLAGS_FOR_CONTAINER` — it points PyPI glfw at the system
    dual-build libglfw for MVP's imgui_bundle; hanoi has no glfw, so it's meaningless (and points at a
    lib that may not be installed).
  - The `mesa-dri-drivers`/`mesa-libGLU-devel` packages are for hardware GL; hanoi's `wx.GraphicsContext`
    2D renderer is Cairo/GTK, not GL. `DRI_DEVICE` is harmless (auto-skips without `/dev/dri`) and worth
    keeping for parity, but the mesa GL *packages* may be unnecessary — see Q3.
- **Libraries may already be mostly present** via `python3-wxpython4`'s transitive deps (gtk3, libX*).
  The user asked for them installed **explicitly** and **by default** (the MVP way), so create the
  script regardless; Q3 is about trimming it to what wx/GTK actually needs rather than copying MVP's
  GL-oriented list wholesale.
- The user's request is "libraries installed by default, flags set by default, in the same way as
  modelviewprojection" — MVP uses a plain `USE_X_WINDOWS ?= 1` (always on). Q1 reconciles that literal
  ask with the minimal-nested standard hanoi just adopted.

## Open questions — resolved 2026-09-16 (maintainer)

1. **`USE_X_WINDOWS` default form → plain `?= 1`.** The maintainer chose MVP's literal form: on
   everywhere, including nested builds, so the GUI works from a nested shell too. This is a deliberate
   departure from the minimal-nested standard's "flip GUI off when nested" default (hanoi has no
   headless-Mesa gate), accepted for parity with modelviewprojection and "installed by default".
2. **Explicit install script → yes.** Added `entrypoint/03-install-xwindows.sh` even though
   `python3-wxpython4` pulls gtk3/libX* transitively, so the dependency is intentional.
3. **Library set → trimmed.** Dropped MVP's `mesa-dri-drivers`/`mesa-libGLU-devel` (OpenGL, unused by
   wx's 2D Cairo renderer) and glfw. Installed: `gtk3`, the `libX*` interaction set, and
   `libwayland-client`/`libwayland-cursor`/`libxkbcommon` for the GTK Wayland backend.
4. **Verification → agent, headless via Xvfb.** Done (see Plan). Xvfb exercises only the X11 path;
   confirming the real Wayland session remains a maintainer check on a live desktop.
