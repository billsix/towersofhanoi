#!/usr/bin/env bash
#
# Proof harness for tasks/enable-gui-wayland-x-passthrough.md: confirm the hanoi image
# built with USE_X_WINDOWS=1 has the GUI client libraries and can open the wxPython GUI
# headlessly under Xvfb (the X11 path). Real Wayland is verified by the maintainer on a
# live session; Xvfb only exercises X11.
#
# Run in-container from the repo root, e.g.:
#   make shell-exec SCRIPT=tasks/adhoc/enable-gui-wayland-x-passthrough/verify-gui.sh
#
# Multiple checks, so accumulate a non-zero exit if any fails.
set -uo pipefail
status=0

echo "== X11/Wayland client libs present in the image =="
for p in gtk3 libX11 libXrender libXi libwayland-client libwayland-cursor libxkbcommon python3-wxpython4; do
    if rpm -q "$p" >/dev/null 2>&1; then
        echo "  ok       $p"
    else
        echo "  MISSING  $p"; status=1
    fi
done

echo "== Xvfb available (install into this ephemeral container if absent) =="
command -v Xvfb >/dev/null 2>&1 || dnf install -y xorg-x11-server-Xvfb >/dev/null 2>&1
if command -v Xvfb >/dev/null 2>&1; then echo "  ok       Xvfb"; else echo "  Xvfb unavailable"; exit 1; fi

echo "== wxPython creates an App + Frame under Xvfb =="
if xvfb-run -a python3 - <<'PY'
import wx
app = wx.App()
frame = wx.Frame(None, title="hanoi", size=(320, 220))
frame.Show()
print("  ok       wxPython", wx.version(), "App + Frame created")
PY
then :; else echo "  wx App/Frame FAILED"; status=1; fi

echo "== hanoi-gui entry point launches under Xvfb (no lib/display crash) =="
uv pip install --no-deps --no-index --no-build-isolation --system -e /hanoi/python >/dev/null 2>&1
out=$(xvfb-run -a timeout 4 hanoi-gui 2>&1); rc=$?
# Real failures only. Exclude benign "Gtk-Message: Failed to load module
# \"...-gtk-module\"" warnings (optional GTK theme/menu modules, absent in a minimal image).
errs=$(printf '%s\n' "$out" | grep -iE 'Traceback|ImportError|No module named|cannot open display|undefined symbol|core dumped' | grep -viE 'Gtk-Message')
if [ -n "$errs" ]; then
    echo "  hanoi-gui ERROR:"; printf '%s\n' "$out" | tail -n 15; status=1
else
    echo "  ok       hanoi-gui ran under Xvfb (rc=$rc; only benign Gtk-Message module warnings, if any)"
fi

echo "== result =="
[ "$status" -eq 0 ] && echo "  PASS" || echo "  FAIL"
exit $status
