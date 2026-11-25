#!/bin/bash
# Format and lint only the Python files this task changed (the repo gate rewrites everything).
source /venv/bin/activate; cd /hanoi-python || exit 1
F="src/hanoigame/commands.py src/hanoigame/engine.py src/hanoigame/hanoicli.py src/hanoigame/hanoigame.py src/hanoigame/presenter.py src/hanoigame/recipe.py"
ruff format $F
ruff check --output-format concise --exit-zero $F
