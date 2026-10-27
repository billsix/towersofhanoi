#!/bin/env bash
# Format our own C++ with clang-format -- never the vendored imgui/ or doctest/
# trees or the build dirs.
[ -d /hanoi-cpp ] && cd /hanoi-cpp

# Safe by shape: a single find ... -print0 | xargs -0 pipeline (xargs's exit propagates).
status=0
find . -path ./imgui -prune -o -path ./doctest -prune -o \
  -path ./build -prune -o -path ./build-web -prune -o \
  \( -name '*.cpp' -o -name '*.hpp' -o -name '*.h' \) -print0 \
  | xargs -0 -r clang-format -i || status=1
exit $status
