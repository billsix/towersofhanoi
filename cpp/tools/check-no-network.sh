#!/usr/bin/env bash
# Static "no-network" gate for hanoi's C++ Dear ImGui WebAssembly build.
# The wasm app (`make webassembly` / `make serve`) must run ENTIRELY from local
# assets, with no network -- a hard maintainer constraint. This fails (nonzero
# exit) if the committed web SOURCE references a REMOTE resource, so a later edit
# cannot quietly add a CDN <script>, a web-font @import, or a remote asset.
#
# What is scanned: cpp/shell.html -- the Emscripten --shell-file template that
# becomes the generated web/index.html. ONLY this file (plus any committed app
# .css/.js added here later): deliberately NOT a blanket cpp/**/*.html, because
#   - web/ is the gitignored emscripten OUTPUT (gate the source, not the artifact);
#   - the vendored emacs tree (entrypoint/dotfiles/.emacs.d/elpa/) contains
#     third-party package HTML with its own CDN <script>/<link> tags that never
#     ship in the app and must not fail this gate.
#
# Allowed (NOT flagged): relative paths, data: URIs. Flagged: http(s)://, ws(s)://
# anywhere, and protocol-relative //host in src=/href=/url(). A URL in a comment
# trips it too, by design; allow-list a genuine exception here with a reason.
#
# Portable: run from `make check-no-network` (host-side -- needs no image/toolchain)
# or directly anywhere; needs only bash + grep.
# Rationale: tasks/cpp-wasm-no-network-static-gate.md.
set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cpp_dir="$(cd "$here/.." && pwd)"

# The committed web source files of the app (NOT the generated web/, NOT elpa/).
web_files=(
	"$cpp_dir/shell.html"
)

pattern='(https?|wss?)://|(src|href)=["'\''"]?//|url\(//'

hits="$(grep -nE "$pattern" "${web_files[@]}" 2>/dev/null)"

if [ -n "$hits" ]; then
	echo "FAIL: remote resource reference(s) in the C++ wasm web source -- must be local/offline:" >&2
	echo "$hits" >&2
	echo "If this is a genuine local-only use, allow-list it in cpp/tools/check-no-network.sh with a reason." >&2
	exit 1
fi
echo "OK: no remote resource references in the C++ wasm web source (shell.html)."
