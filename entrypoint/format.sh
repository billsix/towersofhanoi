#!/bin/env bash

cd /hanoi || exit 1

# Every step runs, but the script exits nonzero if ANY step failed --
# otherwise the exit code is the LAST command's alone, and a `ruff check`
# failure is silently masked by a clean `ruff format` (the flaw that hid
# ty errors behind a green format gate in gacalc, found 2026-07-29).
status=0
ruff check . --fix || status=1
ruff format --line-length=80 || status=1
exit $status
