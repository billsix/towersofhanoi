# Made the native egui front-end start under X11 (added `libxkbcommon-x11` to the Rust image)

**Completed:** 2026-11-26
**Created:** 2026-11-26 (William Emerison Six <billsix@gmail.com>: "make a task to fix that with xkbcommon x11, or see if it can run in wayland"). Go-ahead the same day.
**Source:** `tasks/archive/2026/11/25/apply-naming-and-scope-rules-per-language.md` ("Second pass": the egui app was the one GUI not run).

## What was done

`rust/entrypoint/01-install-rust-base.sh` installs `libxkbcommon-x11`, with a line in its header comment saying why. `cd rust && make egui` now starts on an X11 display; before, it stopped at start with a message naming `libxkbcommon-x11.so`.

## Why it failed, and only on X11

`rust/hanoi-egui/Cargo.lock` holds both winit backends (`wayland-client`, `smithay-client-toolkit`, `x11rb`, `x11-dl`, `xkbcommon-dl`). `xkbcommon-dl` opens its libraries at run time, so nothing fails at build or link time. The image already had `libxkbcommon`, the three `libwayland-*` libraries, `mesa-libEGL` and `mesa-dri-drivers` (pulled in by the GTK packages); it lacked only `libxkbcommon-x11`.

`PLAY_FLAGS` in `rust/Makefile` passes both the X11 and the Wayland environment into the container, and winit chooses Wayland when `WAYLAND_DISPLAY` is set. So the X11 path is taken on an X11 session, or under Xvfb, which is how an agent checks a GUI in the sandbox.

## Measurements (2026-11-26, in the sandbox)

| Display | Image | Result |
|---|---|---|
| X11 (Xvfb `:99`, `DISPLAY` only) | before the change | stops at start; the message names `libxkbcommon-x11.so` |
| X11 (Xvfb `:99`, `DISPLAY` only) | rebuilt with the change (`make image`) | starts; a screenshot shows the menu bar, the board with three discs, the History panel and the How to Play dialog |
| Wayland (headless `weston`, `WAYLAND_DISPLAY` and `XDG_RUNTIME_DIR` only, no `DISPLAY`) | before the change | starts and keeps running until stopped after 60 s; Mesa printed warnings about finding no GPU device. No screenshot was obtained (`weston-screenshooter` did not return), so the drawing was not seen |

## How the X11 check was run

Xvfb `:99 -screen 0 1280x800x24` in the sandbox; the `make egui` recipe's `podman run` line with `-e DISPLAY=:99 -v /tmp/.X11-unix:/tmp/.X11-unix` and no Wayland variables; after the build, `import -display :99 -window root shot.png`, and the image was read. `weston` is not in the sandbox image; it was installed for the one Wayland measurement.

## Not done

Nothing was clicked or dragged in the egui app, and it was not run on a real display; the on-display checks of the four GUIs stay with the maintainer. `rust/CLAUDE.md` does not list the image's packages, so it needed no change.
