#!/usr/bin/env bash
#
# update-imgui.sh -- re-vendor Dear ImGui into cpp/imgui/ at a given ref, OVERWRITING the
# vendored files. The ref can be a branch, a tag, or a commit SHA.
#
#   Usage:  tools/update-imgui.sh <ref>        (or: make update-imgui IMGUI_REF=<ref>)
#   e.g.    tools/update-imgui.sh v1.92.0
#           tools/update-imgui.sh master
#           tools/update-imgui.sh 1d2c4e8b...     (a commit SHA)
#
# Runs on the host (needs git); only clones + copies, no container. A full clone is used
# so an arbitrary SHA can be checked out (a shallow clone can only fetch a branch/tag tip).
set -euo pipefail

REF="${1:?usage: update-imgui.sh <imgui branch|tag|SHA>}"

# Repo-relative so this works from any checkout: the script lives in cpp/tools/.
CPP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$CPP_DIR/imgui"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

git clone https://github.com/ocornut/imgui.git "$TMP"
git -C "$TMP" checkout "$REF"

# The exact set the build compiles (core + the SDL2 and OpenGL3 backends) -- keep this
# list in sync with cpp/CMakeLists.txt if the backend ever changes.
mkdir -p "$DEST/backends"
cp "$TMP"/imgui.h "$TMP"/imgui.cpp "$TMP"/imgui_internal.h \
   "$TMP"/imgui_draw.cpp "$TMP"/imgui_tables.cpp "$TMP"/imgui_widgets.cpp \
   "$TMP"/imconfig.h "$TMP"/imstb_rectpack.h "$TMP"/imstb_textedit.h \
   "$TMP"/imstb_truetype.h "$TMP"/LICENSE.txt "$DEST"/
cp "$TMP"/backends/imgui_impl_sdl2.cpp "$TMP"/backends/imgui_impl_sdl2.h \
   "$TMP"/backends/imgui_impl_opengl3.cpp "$TMP"/backends/imgui_impl_opengl3.h \
   "$TMP"/backends/imgui_impl_opengl3_loader.h "$DEST"/backends/

VER="$(grep -m1 '#define IMGUI_VERSION ' "$DEST/imgui.h" | sed 's/.*"\(.*\)".*/\1/')"
echo "Vendored Dear ImGui $VER (ref: $REF) into $DEST"
echo "NOTE: if the version changed, update the pin noted in cpp/README.md and cpp/CLAUDE.md,"
echo "      then rebuild and re-verify: make gui  (native)  and  make webassembly  (wasm)."
