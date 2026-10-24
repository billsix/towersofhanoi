# Fail-fast setup: a failed editable install aborts rather than dropping you into a
# half-set-up tree. The final `exec bash` is a FRESH bash not under -e, so
# interactive/script behaviour is unchanged. The package + its deps are already baked
# into the image; this re-installs editable from the live mount so host edits win.
set -e
cd /hanoi-python
uv pip install --no-deps --no-index --no-build-isolation --system -e .
# No args -> interactive shell. Args (a `-c '...'` payload from `make shell-exec`) ->
# run them after setup, in a fresh bash not under -e.
exec bash "$@"
