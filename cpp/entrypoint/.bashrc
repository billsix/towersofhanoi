alias ls='ls --color=auto'

# Two-line prompt: cyan time, green user@host:cwd, then a lambda on its own line.
PS1='\[\e[36m\]┌─(\t) \[\e[32m\]\u@\h:\w\n\[\e[36m\]└─λ \[\e[0m\]'

# Put emcc/em++/emcmake on PATH in interactive shells (when emsdk is installed).
[ -f /opt/emsdk/emsdk_env.sh ] && . /opt/emsdk/emsdk_env.sh >/dev/null 2>&1

# Format the source on shell exit (clang-format via /format.sh).
exit() {
    echo "Formatting on shell exit"
    /format.sh
    builtin exit "$@"
}
