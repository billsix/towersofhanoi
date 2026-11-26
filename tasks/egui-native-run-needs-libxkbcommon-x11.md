# Make the native egui front-end start under X11 (add `libxkbcommon-x11` to the Rust image)

**Status:** proposed — needs go-ahead
**Priority:** 6 (one front-end cannot start on an X11 display; Wayland is unaffected)
**Difficulty:** 1 (one package in one install script, an image rebuild, one run)
**Created:** 2026-11-26 (William Emerison Six <billsix@gmail.com>: "make a task to fix that with xkbcommon x11, or see if it can run in wayland").
**Source:** `tasks/archive/2026/11/25/apply-naming-and-scope-rules-per-language.md` ("Second pass": the egui app was the one GUI not run).

## BLUF

`cd rust && make egui` stops at start on an X11 display, because the `hanoi-rust` image has no `libxkbcommon-x11.so`, which winit's X11 backend loads at run time. On Wayland the same image runs the app. This task adds the package `libxkbcommon-x11` to `rust/entrypoint/01-install-rust-base.sh`. Done means the rebuilt image starts the egui app on an X11 display (Xvfb in the sandbox is enough) and the board is drawn.

## Context

**What was measured (2026-11-26, in the sandbox, image `hanoi-rust` as built).**

| Display | Image | Result |
|---|---|---|
| X11 (Xvfb `:99`, `DISPLAY` only) | unmodified | stops at start; the message names `libxkbcommon-x11.so` |
| X11 (Xvfb `:99`, `DISPLAY` only) | `dnf install -y libxkbcommon-x11` run first in the same throwaway container | starts; a screenshot shows the menu bar, the board with three discs, the History panel and the How to Play dialog |
| Wayland (headless `weston`, `WAYLAND_DISPLAY` and `XDG_RUNTIME_DIR` only, no `DISPLAY`) | unmodified | starts and keeps running until stopped after 60 s; Mesa printed warnings about finding no GPU device. No screenshot was obtained (`weston-screenshooter` did not return), so the drawing was not seen |

**Why Wayland works and X11 does not.** `rust/hanoi-egui/Cargo.lock` holds both winit backends (`wayland-client`, `smithay-client-toolkit`, `x11rb`, `x11-dl`, `xkbcommon-dl`). `xkbcommon-dl` opens its libraries at run time, so nothing fails at build or link time. The image has `libxkbcommon`, `libwayland-client`, `libwayland-egl`, `libwayland-cursor`, `mesa-libEGL` and `mesa-dri-drivers` (pulled in by the GTK packages), and lacks only `libxkbcommon-x11`.

**Why the maintainer's host probably never showed this.** `PLAY_FLAGS` in `rust/Makefile` passes both the X11 and the Wayland environment into the container, and winit chooses Wayland when `WAYLAND_DISPLAY` is set. The X11 path is taken on an X11 session, or under Xvfb, which is how an agent checks a GUI in the sandbox.

**Files.** `rust/entrypoint/01-install-rust-base.sh` (one alphabetical `dnf install` list; `libxkbcommon-x11` goes after `libtiff-devel`, and its header comment gets one line saying which front-end needs it). `rust/CLAUDE.md` describes the image and the `make egui` target; add the package there if the image's contents are listed.

**How to check under Xvfb** (the method used above): start `Xvfb :99 -screen 0 1280x800x24` in the sandbox; run the `make egui` recipe's `podman run` line with `-e DISPLAY=:99 -v /tmp/.X11-unix:/tmp/.X11-unix` and no Wayland variables; after the build finishes, `import -display :99 -window root shot.png` and read the image. Stop Xvfb by its process id.

**Not installed in the sandbox image:** `weston`. It was installed for the Wayland measurement with `dnf install -y weston` and is gone at the next sandbox start; the X11 check does not need it.

## Plan

- [ ] Add `libxkbcommon-x11` to `rust/entrypoint/01-install-rust-base.sh`; note it in the script's header comment.
- [ ] Rebuild the image (`cd rust && make image`).
- [ ] Run the egui app on Xvfb with `DISPLAY` only; read the screenshot.
- [ ] Update `rust/CLAUDE.md` if it lists the image's packages.

## Open questions

None.
