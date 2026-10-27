cmake_minimum_required(VERSION 3.16)
project(hanoi_cpp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(IMGUI_DIR ${CMAKE_SOURCE_DIR}/imgui)

# Dear ImGui is vendored source (no library/package): compile the core + the SDL2 and
# OpenGL3 backends into the binary. Same list for native and wasm.
add_executable(hanoi-cpp
  main.cpp
  ${IMGUI_DIR}/imgui.cpp
  ${IMGUI_DIR}/imgui_draw.cpp
  ${IMGUI_DIR}/imgui_tables.cpp
  ${IMGUI_DIR}/imgui_widgets.cpp
  ${IMGUI_DIR}/backends/imgui_impl_sdl2.cpp
  ${IMGUI_DIR}/backends/imgui_impl_opengl3.cpp
)
target_include_directories(hanoi-cpp PRIVATE
  ${IMGUI_DIR} ${IMGUI_DIR}/backends ${CMAKE_SOURCE_DIR} ${CMAKE_SOURCE_DIR}/src)
# The engine headers include <doctest/doctest.h> and carry TEST_CASEs beside the
# code; the GUI binary compiles them out with DOCTEST_CONFIG_DISABLE (which still
# needs the header found, hence CMAKE_SOURCE_DIR on the include path). Only the
# `hanoi-tests` executable (below) builds the tests in.
target_compile_definitions(hanoi-cpp PRIVATE DOCTEST_CONFIG_DISABLE)

if(EMSCRIPTEN)
  # Web build: SDL2 + WebGL come from Emscripten; emit web/index.{html,js,wasm}. See
  # tasks/reference/imgui-cpp-native-and-wasm.md for the flag rationale.
  set_target_properties(hanoi-cpp PROPERTIES
    OUTPUT_NAME index SUFFIX ".html"
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/web)
  # -DIMGUI_IMPL_OPENGL_ES3: the OpenGL3 backend needs an explicit GLES build for WebGL
  # (it does NOT auto-select ES for Emscripten); main.cpp then uses an ES3 context +
  # "#version 300 es". Without it, desktop GLSL shaders fail under WebGL and nothing draws.
  target_compile_options(hanoi-cpp PRIVATE
    -sUSE_SDL=2 -sDISABLE_EXCEPTION_CATCHING=1 -DIMGUI_DISABLE_FILE_FUNCTIONS
    -DIMGUI_IMPL_OPENGL_ES3 -Os)
  # -sMIN/MAX_WEBGL_VERSION=2: ES3 == WebGL 2.0, so force a WebGL2 context.
  target_link_options(hanoi-cpp PRIVATE
    -sUSE_SDL=2 -sWASM=1 -sALLOW_MEMORY_GROWTH=1 -sNO_EXIT_RUNTIME=0
    -sNO_FILESYSTEM=1 -sASSERTIONS=1
    -sMIN_WEBGL_VERSION=2 -sMAX_WEBGL_VERSION=2
    --shell-file ${CMAKE_SOURCE_DIR}/shell.html)
else()
  # Native build: system SDL2 (sdl2-compat on Fedora) via pkg-config + OpenGL.
  find_package(PkgConfig REQUIRED)
  pkg_check_modules(SDL2 REQUIRED sdl2)
  target_include_directories(hanoi-cpp PRIVATE ${SDL2_INCLUDE_DIRS})
  target_link_libraries(hanoi-cpp PRIVATE ${SDL2_LIBRARIES} GL dl)
  target_compile_options(hanoi-cpp PRIVATE ${SDL2_CFLAGS_OTHER})

  # The wxWidgets front-end (make wx), built from the shared XRC. Only when
  # wxGTK-devel is present (the USE_WX image) -- QUIET + the FOUND guard so a lean
  # image without wx still configures + builds the ImGui target. wxWidgets is not
  # available under Emscripten, so this is native-only.
  find_package(wxWidgets COMPONENTS xrc html adv core base QUIET)
  if(wxWidgets_FOUND)
    include(${wxWidgets_USE_FILE})
    add_executable(hanoi-wx hanoiwx.cpp)
    target_include_directories(hanoi-wx PRIVATE
      ${CMAKE_SOURCE_DIR} ${CMAKE_SOURCE_DIR}/src)
    target_compile_definitions(hanoi-wx PRIVATE DOCTEST_CONFIG_DISABLE)
    target_link_libraries(hanoi-wx PRIVATE ${wxWidgets_LIBRARIES})
  else()
    message(STATUS "wxWidgets not found -- skipping hanoi-wx (build a USE_WX=1 image for `make wx`).")
  endif()
endif()

# Unit tests: the doctest cases live inline in the engine headers (src/*.hpp); this
# runner TU provides doctest's main and includes the engine so they register. Built
# WITHOUT DOCTEST_CONFIG_DISABLE (the cases compile in) and native-only -- the engine
# is pure C++ (no SDL/GL/wx), so the test build is fast and needs none of the GUI
# stack. `make test` builds this and runs it under ctest.
if(NOT EMSCRIPTEN)
  enable_testing()
  add_executable(hanoi-tests tests/run_tests.cpp)
  target_include_directories(hanoi-tests PRIVATE
    ${CMAKE_SOURCE_DIR} ${CMAKE_SOURCE_DIR}/src)
  add_test(NAME hanoi-tests COMMAND hanoi-tests)
endif()
