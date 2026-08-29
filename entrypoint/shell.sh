# Fail-fast setup: a failed editable install aborts rather than dropping you into /
# running a shell-exec script against a half-set-up tree. The final `exec bash` is a
# FRESH bash not under -e, so interactive/script behaviour is unchanged.
set -e
cd /hanoi/python
uv pip install --no-deps --no-index --no-build-isolation --system -e .
cd ..
# No args -> interactive shell (as before). Args (a `-c '...'` payload from
# `make shell-exec`) -> run them after setup, in a fresh bash not under -e.
exec bash "$@"
