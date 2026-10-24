#!/bin/env bash

[ -d /hanoi-python ] && cd /hanoi-python

# Every step runs, but the script exits nonzero if ANY step failed -- otherwise the
# exit code is the LAST command's alone, and a `ruff check` failure is silently masked
# by a clean `ruff format` (the multi-step-gate rule).
status=0
ruff check . --fix || status=1
# Line width comes from [tool.ruff] line-length in pyproject.toml (single source of
# truth, shared with the E501 lint) -- no per-invocation flag.
ruff format || status=1
exit $status
