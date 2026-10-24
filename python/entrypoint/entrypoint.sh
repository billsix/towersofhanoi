#!/bin/env bash
# Default entrypoint for the Python subproject: install the package editable from the
# mount (so host edits are tested) and run the pytest gate. The Sphinx book + workbook
# are built at the repo root, not here.
set -e
cd /hanoi-python
uv pip install --no-deps --no-index --no-build-isolation --system -e .
pytest --exitfirst --disable-warnings
