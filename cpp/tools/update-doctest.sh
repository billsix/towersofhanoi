#!/usr/bin/env bash
#
# update-doctest.sh -- re-vendor the doctest single-header test framework into
# cpp/doctest/ at a given ref, OVERWRITING the vendored files. The ref can be a
# branch, a tag, or a commit SHA.
#
#   Usage:  tools/update-doctest.sh <ref>        (or: make update-doctest DOCTEST_REF=<ref>)
#   e.g.    tools/update-doctest.sh v2.5.3
#           tools/update-doctest.sh master
#
# doctest is a SINGLE header (doctest/doctest.h) plus its MIT LICENSE.txt, so this
# fetches just those two files with curl -- no clone needed (a raw URL resolves a
# branch, tag, or SHA alike). Runs on the host (needs curl); no container.
set -euo pipefail

REF="${1:?usage: update-doctest.sh <doctest branch|tag|SHA>}"

# Repo-relative so this works from any checkout: the script lives in cpp/tools/.
CPP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$CPP_DIR/doctest"
RAW="https://raw.githubusercontent.com/doctest/doctest/$REF"

mkdir -p "$DEST"
curl -fsSL "$RAW/doctest/doctest.h" -o "$DEST/doctest.h"
curl -fsSL "$RAW/LICENSE.txt" -o "$DEST/LICENSE.txt"

# DOCTEST_VERSION_STR is a macro concatenation, not a literal, so compose the
# version from the three numeric component macros instead.
ver_part() { grep -m1 "#define $1 " "$DEST/doctest.h" | awk '{print $3}'; }
VER="$(ver_part DOCTEST_VERSION_MAJOR).$(ver_part DOCTEST_VERSION_MINOR).$(ver_part DOCTEST_VERSION_PATCH)"
echo "Vendored doctest $VER (ref: $REF) into $DEST"
echo "NOTE: if the version changed, update the pin noted in cpp/README.md and cpp/CLAUDE.md,"
echo "      then rebuild + re-verify: make test."
