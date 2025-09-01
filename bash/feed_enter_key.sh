#!/usr/bin/env bash
# Usage: ./press_enter.sh <interval> <command> [args...]

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <interval_seconds> <command> [args...]"
    exit 1
fi

interval="$1"
shift

# Run the target program in a coprocess so we can feed it input
coproc TARGET { "$@"; }

# Send Enter every $interval seconds until the process exits
while kill -0 "$TARGET_PID" 2>/dev/null; do
    printf '\n' >&"${TARGET[1]}"
    sleep "$interval"
done

