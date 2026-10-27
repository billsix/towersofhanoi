// Copyright (c) 2026 William Emerison Six -- GNU GPL v2 or later.
//
// The doctest runner entry point for the C++ engine tests. The actual
// TEST_CASEs live BESIDE the code they test, in the engine headers
// (src/model.hpp, src/presenter.hpp, src/recipe.hpp). The GUI/wasm targets
// compile those cases out via -DDOCTEST_CONFIG_DISABLE (set per-target in
// CMakeLists.txt); this executable builds them in. This TU provides doctest's
// implementation + main() (via DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN, which must
// be defined before the first include of the header) and then pulls in the
// engine so those inline cases are registered. `make test` builds this as
// `hanoi-tests` and runs it under ctest.
#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include <doctest/doctest.h>

// recipe.hpp includes model.hpp and presenter.hpp, so this one include brings
// in all three headers' inline TEST_CASEs.
#include "recipe.hpp"
