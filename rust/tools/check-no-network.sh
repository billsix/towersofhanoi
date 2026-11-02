#!/usr/bin/env bash
# Static "no-network" gate for hanoi's Rust web targets: the Tauri frontend
# (tauri/frontend/) and the egui WebAssembly build (hanoi-egui/). Both UIs must
# run ENTIRELY from local / embedded assets, with no network -- a hard maintainer
# constraint. This fails (nonzero exit) if any committed web source references a
# REMOTE resource, so a later edit cannot quietly add a CDN <script>, a web-font
# @import, a remote <img>, or a fetch()/WebSocket to a remote host without CI
# catching it.
#
# Allowed (NOT flagged): relative paths (main.js, ./style.css), data: URIs, the
#   window.__TAURI__ global and Tauri invoke() (local IPC, not network), and
#   Trunk's `data-trunk rel="rust"` build directive (carries no scheme or //host).
# Flagged: http(s):// and ws(s):// anywhere (covers src=/href=/url()/@import/
#   import-from/fetch()/new WebSocket), and protocol-relative //host in
#   src=/href=/url(...). A URL in a *comment* trips it too, by design (conservative);
#   if a genuine exception is ever needed, allow-list it here with a reason.
#
# Portable by design: run from `make type-check` inside the container, or directly
# on the host / CI runner -- it needs only bash + grep and resolves its own paths.
# Rationale + the full allow/deny list: tasks/tauri-frontend-no-network-static-gate.md
# and tasks/egui-web-no-network-static-gate.md.
set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
rust_dir="$(cd "$here/.." && pwd)"

# Committed web SOURCE of each Rust web target -- never the generated output
# (tauri embeds frontend/ at build; egui's trunk output is the gitignored dist/).
# A directory is recursed over web files only; the egui entry files are named.
scan_dir="$rust_dir/tauri/frontend"
egui_files=(
	"$rust_dir/hanoi-egui/index.html"
	"$rust_dir/hanoi-egui/Trunk.toml"
)

pattern='(https?|wss?)://|(src|href)=["'\''"]?//|url\(//'

hits="$(
	grep -rnE --include='*.html' --include='*.js' --include='*.css' \
		"$pattern" "$scan_dir" 2>/dev/null
	grep -nE "$pattern" "${egui_files[@]}" 2>/dev/null
)"

if [ -n "$hits" ]; then
	echo "FAIL: remote resource reference(s) in a Rust web target -- these must be local/offline:" >&2
	echo "$hits" >&2
	echo "If this is a genuine local-only use, allow-list it in rust/tools/check-no-network.sh with a reason." >&2
	exit 1
fi
echo "OK: no remote resource references in the Rust web targets (Tauri frontend, egui-web)."
