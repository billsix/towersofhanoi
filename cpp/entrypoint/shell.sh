# C++ subproject dev-shell setup. Source the emsdk env (when present) so emcc/em++/
# emcmake are on PATH for `make webassembly`; a lean image without emsdk simply skips it.
set -e
[ -f /opt/emsdk/emsdk_env.sh ] && . /opt/emsdk/emsdk_env.sh >/dev/null 2>&1 || true
cd /hanoi-cpp
# No args -> interactive shell. Args (a `-c '...'` payload from `make shell-exec`) -> run
# them after setup, in a fresh bash not under -e.
exec bash "$@"
