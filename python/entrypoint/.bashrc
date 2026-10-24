# Interactive-shell setup for `make shell` (bind-mounted, so edits are live without a
# rebuild). Modelled on the maintainer's per-language dev-container shells.

alias ls='ls --color=auto'

# Two-line prompt: cyan time, green user@host:cwd, then a lambda on its own line.
PS1='\[\e[36m\]┌─(\t) \[\e[32m\]\u@\h:\w\n\[\e[36m\]└─λ \[\e[0m\]'

# Format the source on shell exit (ruff via /format.sh).
exit() {
    echo "Formatting on shell exit"
    /format.sh
    builtin exit "$@"
}
