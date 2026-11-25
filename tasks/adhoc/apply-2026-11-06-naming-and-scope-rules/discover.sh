#!/bin/bash
# Survey for the 2026-11-06 naming and scope rules (rules 1-4); writes data/candidates.txt.
exec python3 "$(dirname "$0")/discover.py" python/src python/tests python/tools tools
