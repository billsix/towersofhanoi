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
  ${IMGUI_DIR} ${IMGUI_DIR}/backends ${CMAKE_SOURCE_DIR}/src)

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
endif()
