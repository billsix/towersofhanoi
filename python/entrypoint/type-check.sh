#!/bin/env bash

# Type-check the hanoigame package (src) and tests with ty (Astral).
#
# Portable: runs in-container (cd into the mounted subproject) AND on the host from the
# python/ dir -- the `cd` no-ops when /hanoi-python isn't present, so a host caller
# already in python/ works unchanged.
[ -d /hanoi-python ] && cd /hanoi-python

# Every step runs, but the script exits nonzero if ANY step failed -- a bare command
# sequence would report only the LAST command's status (the multi-step-gate rule).
# ty searches only /usr/lib*/pythonX/site-packages for third-party code, but uv
# installs the pinned packages (numpy, glfw, PyOpenGL, gacalc, pytest) under
# /usr/local; hand ty every site-packages directory the interpreter itself uses.
search_paths=()
for dir in $(python3 -c 'import site; print(" ".join(site.getsitepackages()))'); do
    [ -d "$dir" ] && search_paths+=(--extra-search-path "$dir")
done

status=0
ty check "${search_paths[@]}" src || status=1
ty check "${search_paths[@]}" tests || status=1
exit $status
