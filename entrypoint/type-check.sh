#!/bin/env bash

# Type-check the Python package (src) and tests with ty (Astral).
#
# Portable: runs in-container (cd into the mounted repo's python/ dir) AND on
# the host from the repo's python/ dir -- the `cd` no-ops when /hanoi/python
# isn't present, so a host caller that is already in python/ works unchanged.
[ -d /hanoi/python ] && cd /hanoi/python

# Every step runs, but the script exits nonzero if ANY step failed -- a bare
# command sequence would report only the LAST command's status, silently
# masking an earlier failure (the multi-step-gate rule).
status=0
ty check src || status=1
ty check tests || status=1
exit $status
