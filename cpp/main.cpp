// Copyright (c) 2026 William Emerison Six -- GNU GPL v2 or later.
//
// Dear ImGui front-end for Towers of Hanoi, building native (SDL2 + OpenGL3)
// and, under Emscripten, as WebAssembly. Feature parity with the Python
// wxPython GUI: a menubar for disk-count / relabelling / recipes, the board
// coloured by LABEL (so colour follows the label after relabelling), legal
// moves shown in the current labels, and recipe record/replay with the
// label->peg rebinding shown. Game logic is the ported engine (src/*.hpp), kept
// in sync with the canonical Python (the behaviour oracle).

#include "imgui.h"
#include "imgui_impl_opengl3.h"
#include "imgui_impl_sdl2.h"
#include <SDL.h>
#include <SDL_opengl.h>
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#include <emscripten/html5.h>
#endif

#include "model.hpp"
#include "presenter.hpp"
#include "recipe.hpp"

#include <array>
#include <cstdio>
#include <string>
#include <vector>

namespace {

// Blue / gold / red, indexed by 0-indexed LABEL (not physical peg) -- the peg
// colour tracks its label so the student keeps "label 1 is the blue peg" after
// relabelling.
const std::array<ImU32, 3> kLabelColors{IM_COL32(70, 130, 220, 255),
                                        IM_COL32(220, 190, 60, 255),
                                        IM_COL32(220, 80, 80, 255)};

// The whole app state.
struct App {
  hanoi::Game game{3};
  hanoi::Labelling labelling = hanoi::Labelling::OneTwoThree;
  hanoi::Recorder recorder;
  hanoi::RecipeRegistry registry;
  char name_buf[64] = "";
  std::string status;     // last recipe-replay / action message
  bool open_save = false; // request to open the save-recipe modal

  void new_game(int n) {
    game = hanoi::Game(n);
    recorder.reset();
    status.clear();
  }
  // Apply a physical move and record it in default-label space (from_peg+1,
  // to_peg+1).
  void do_move(const hanoi::Move &m) {
    game.apply(m);
    recorder.record(m.from_peg + 1, m.to_peg + 1);
  }
};

// Draw the three pegs (coloured by label) + their disks with draw-list
// primitives.
void draw_board(const App &app) {
  const hanoi::Game &game = app.game;
  ImDrawList *dl = ImGui::GetWindowDrawList();
  const ImVec2 origin = ImGui::GetCursorScreenPos();
  const float board_w = ImGui::GetContentRegionAvail().x;
  const float board_h = 260.0f;
  const float peg_gap = board_w / 3.0f;
  const float base_y = origin.y + board_h;
  const float disk_h = 20.0f;
  const float max_disk_w = peg_gap * 0.9f;
  const int n = game.num_disks() > 0 ? game.num_disks() : 1;

  for (int peg = 0; peg < 3; ++peg) {
    const float cx = origin.x + peg_gap * (static_cast<float>(peg) + 0.5f);
    const int label = hanoi::change_labels_on_pegs(app.labelling, peg);
    const ImU32 peg_col = kLabelColors[label];
    // peg vertical, coloured by its label
    dl->AddLine(ImVec2(cx, base_y), ImVec2(cx, origin.y + 12.0f), peg_col,
                5.0f);
    // disks
    const std::vector<int> &stack = game.towers()[peg];
    for (std::size_t level = 0; level < stack.size(); ++level) {
      const int size = stack[level];
      const float w =
          max_disk_w * (static_cast<float>(size) / static_cast<float>(n));
      const float y = base_y - disk_h * (static_cast<float>(level) + 1.0f);
      const ImVec2 a(cx - w / 2.0f, y);
      const ImVec2 b(cx + w / 2.0f, y + disk_h - 3.0f);
      dl->AddRectFilled(a, b, IM_COL32(210, 210, 215, 255), 4.0f);
      dl->AddRect(a, b, IM_COL32(30, 30, 40, 255), 4.0f);
    }
    // the current label under the peg, in the label's colour
    const float lx = cx - 4.0f;
    char lbl[2] = {static_cast<char>('1' + label), '\0'};
    dl->AddText(ImVec2(lx, base_y + 6.0f), peg_col, lbl);
  }
  ImGui::Dummy(ImVec2(board_w, board_h + 32.0f));
}

void draw_menubar(App &app) {
  if (!ImGui::BeginMenuBar()) {
    return;
  }
  if (ImGui::BeginMenu("Game")) {
    if (ImGui::BeginMenu("New game (disks)")) {
      for (int n = 1; n <= 8; ++n) {
        const std::string item = std::to_string(n) + " disks";
        if (ImGui::MenuItem(item.c_str(), nullptr, app.game.num_disks() == n)) {
          app.new_game(n);
        }
      }
      ImGui::EndMenu();
    }
    if (ImGui::MenuItem("Restart")) {
      app.new_game(app.game.num_disks());
    }
    ImGui::EndMenu();
  }
  if (ImGui::BeginMenu("Relabel")) {
    for (const hanoi::Labelling l : hanoi::kAllLabellings) {
      if (ImGui::MenuItem(hanoi::labelling_name(l), nullptr,
                          app.labelling == l)) {
        app.labelling = l;
      }
    }
    ImGui::EndMenu();
  }
  if (ImGui::BeginMenu("Recipe")) {
    const std::string rec =
        "Recording: " + std::to_string(app.recorder.moves().size()) + " moves";
    ImGui::MenuItem(rec.c_str(), nullptr, false, false); // info, disabled
    if (ImGui::MenuItem("Save recording as...", nullptr, false,
                        !app.recorder.moves().empty())) {
      app.open_save = true;
    }
    if (ImGui::MenuItem("Reset recording", nullptr, false,
                        !app.recorder.moves().empty())) {
      app.recorder.reset();
    }
    ImGui::Separator();
    if (ImGui::BeginMenu("Replay", app.registry.size() > 0)) {
      for (const std::string &name : app.registry.names()) {
        if (ImGui::MenuItem(name.c_str())) {
          const hanoi::Recipe *r = app.registry.get(name);
          const std::vector<hanoi::StepResult> res =
              hanoi::apply(*r, app.game, app.labelling);
          int applied = 0;
          std::string err;
          for (const hanoi::StepResult &s : res) {
            if (s.ok()) {
              ++applied;
            } else {
              err = *s.error;
            }
          }
          app.status = "Replayed '" + name + "': " + std::to_string(applied) +
                       "/" + std::to_string(r->default_moves.size()) +
                       " moves" + (err.empty() ? "" : " -- stopped: " + err);
        }
      }
      ImGui::EndMenu();
    }
    ImGui::EndMenu();
  }
  ImGui::EndMenuBar();
}

// The save-recipe modal (name input).
void draw_save_modal(App &app) {
  if (app.open_save) {
    ImGui::OpenPopup("Save recipe");
    app.open_save = false;
  }
  if (ImGui::BeginPopupModal("Save recipe", nullptr,
                             ImGuiWindowFlags_AlwaysAutoResize)) {
    ImGui::TextUnformatted("Name this recipe:");
    ImGui::InputText("##name", app.name_buf, sizeof(app.name_buf));
    const bool has_name = app.name_buf[0] != '\0';
    if (ImGui::Button("Save") && has_name) {
      app.registry.save(
          app.recorder.to_recipe(app.name_buf, app.game.num_disks()));
      app.status = std::string("Saved recipe '") + app.name_buf + "'.";
      app.name_buf[0] = '\0';
      ImGui::CloseCurrentPopup();
    }
    ImGui::SameLine();
    if (ImGui::Button("Cancel")) {
      ImGui::CloseCurrentPopup();
    }
    ImGui::EndPopup();
  }
}

void draw_frame(App &app) {
  ImGuiIO &io = ImGui::GetIO();
  ImGui::SetNextWindowPos(ImVec2(0, 0));
  ImGui::SetNextWindowSize(io.DisplaySize);
  const ImGuiWindowFlags flags =
      ImGuiWindowFlags_MenuBar | ImGuiWindowFlags_NoTitleBar |
      ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoMove |
      ImGuiWindowFlags_NoCollapse | ImGuiWindowFlags_NoBringToFrontOnFocus;
  ImGui::Begin("Towers of Hanoi", nullptr, flags);

  draw_menubar(app);
  draw_save_modal(app);

  ImGui::Text("Moves: %d", app.game.current_moves());
  ImGui::SameLine();
  if (app.game.check_win_condition()) {
    ImGui::TextColored(ImVec4(0.3f, 0.9f, 0.3f, 1.0f), "  -- solved!");
  }

  draw_board(app);

  // All six moves are ALWAYS shown in a fixed layout (shown in the current
  // labels); moves that aren't currently legal are disabled rather than hidden
  // -- so the buttons don't jump around as the legal set changes (matching the
  // wx version).
  ImGui::Separator();
  ImGui::TextUnformatted("Moves (current labels; illegal ones disabled):");
  std::array<bool, 9> legal{};
  for (const hanoi::Move &m : app.game.move_options()) {
    legal[static_cast<std::size_t>(m.from_peg * 3 + m.to_peg)] = true;
  }
  static constexpr std::array<std::array<int, 2>, 6> kPairs{
      {{0, 1}, {0, 2}, {1, 0}, {1, 2}, {2, 0}, {2, 1}}};
  for (const std::array<int, 2> &pair : kPairs) {
    const int fp = pair[0];
    const int tp = pair[1];
    const int from_label = hanoi::change_labels_on_pegs(app.labelling, fp) + 1;
    const int to_label = hanoi::change_labels_on_pegs(app.labelling, tp) + 1;
    // "N -> M" visible, with a stable per-physical-pair ImGui id after '##'.
    char btn[24];
    std::snprintf(btn, sizeof(btn), "%d -> %d##%d%d", from_label, to_label, fp,
                  tp);
    ImGui::BeginDisabled(!legal[static_cast<std::size_t>(fp * 3 + tp)]);
    if (ImGui::Button(btn)) {
      app.do_move(hanoi::Move{fp, tp});
    }
    ImGui::EndDisabled();
    ImGui::SameLine();
  }
  ImGui::NewLine();

  // The rebinding: under a non-default labelling, show each recipe label ->
  // physical peg.
  if (app.labelling != hanoi::Labelling::OneTwoThree) {
    ImGui::Separator();
    ImGui::TextUnformatted("Rebinding (a recipe's labels -> physical pegs, "
                           "because you relabelled):");
    const std::array<std::array<int, 2>, 3> rb =
        hanoi::rebinding(app.labelling);
    for (const std::array<int, 2> &pair : rb) {
      ImGui::SameLine();
      ImGui::Text("  label %d -> peg %d", pair[0], pair[1]);
    }
    ImGui::NewLine();
  }

  if (!app.status.empty()) {
    ImGui::Separator();
    ImGui::TextWrapped("%s", app.status.c_str());
  }

  ImGui::End();
}

struct Frame {
  SDL_Window *window = nullptr;
  SDL_GLContext gl_context = nullptr;
  ImGuiIO *io = nullptr;
  App app;
  bool done = false;
};

void main_loop(void *arg) {
  Frame &f = *static_cast<Frame *>(arg);
#ifdef __EMSCRIPTEN__
  // Keep the SDL window (and GL drawable) matching the browser canvas's CSS
  // size, so the app fills the page 1:1 (mouse coordinates stay aligned).
  double css_w = 0.0;
  double css_h = 0.0;
  if (emscripten_get_element_css_size("#canvas", &css_w, &css_h) ==
          EMSCRIPTEN_RESULT_SUCCESS &&
      css_w > 0 && css_h > 0) {
    SDL_SetWindowSize(f.window, static_cast<int>(css_w),
                      static_cast<int>(css_h));
  }
#endif
  SDL_Event event;
  while (SDL_PollEvent(&event)) {
    ImGui_ImplSDL2_ProcessEvent(&event);
    if (event.type == SDL_QUIT) {
      f.done = true;
    }
  }
  ImGui_ImplOpenGL3_NewFrame();
  ImGui_ImplSDL2_NewFrame();
  ImGui::NewFrame();
  draw_frame(f.app);
  ImGui::Render();
  glViewport(0, 0, static_cast<int>(f.io->DisplaySize.x),
             static_cast<int>(f.io->DisplaySize.y));
  glClearColor(0.11f, 0.11f, 0.13f, 1.0f);
  glClear(GL_COLOR_BUFFER_BIT);
  ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
  SDL_GL_SwapWindow(f.window);
}

} // namespace

int main(int, char **) {
  if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_TIMER) != 0) {
    SDL_Log("SDL_Init error: %s", SDL_GetError());
    return 1;
  }
  // GL/GLSL version. On the web, imgui's OpenGL3 backend needs an explicit GLES
  // build (CMake compiles the wasm target with -DIMGUI_IMPL_OPENGL_ES3); the
  // SDL context must then be an ES 3.0 / WebGL 2.0 context and the shader
  // version "#version 300 es" -- otherwise desktop GLSL shaders fail to compile
  // under WebGL and nothing renders. Native Linux uses desktop GL 3.0 + GLSL
  // 130.
#ifdef __EMSCRIPTEN__
  const char *glsl_version = "#version 300 es";
  SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_ES);
  SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
  SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 0);
#else
  const char *glsl_version = "#version 130";
  SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
  SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 0);
#endif
  SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1);
  SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 24);

  const auto flags = static_cast<SDL_WindowFlags>(
      SDL_WINDOW_OPENGL | SDL_WINDOW_RESIZABLE | SDL_WINDOW_ALLOW_HIGHDPI);
  Frame frame;
  frame.window = SDL_CreateWindow("Towers of Hanoi", SDL_WINDOWPOS_CENTERED,
                                  SDL_WINDOWPOS_CENTERED, 760, 560, flags);
  frame.gl_context = SDL_GL_CreateContext(frame.window);
  SDL_GL_MakeCurrent(frame.window, frame.gl_context);
  SDL_GL_SetSwapInterval(1);

  IMGUI_CHECKVERSION();
  ImGui::CreateContext();
  frame.io = &ImGui::GetIO();
  ImGui::StyleColorsDark();
  ImGui_ImplSDL2_InitForOpenGL(frame.window, frame.gl_context);
  ImGui_ImplOpenGL3_Init(glsl_version);

#ifdef __EMSCRIPTEN__
  frame.io->IniFilename = nullptr;
  emscripten_set_main_loop_arg(main_loop, &frame, 0, true);
#else
  while (!frame.done) {
    main_loop(&frame);
  }
  ImGui_ImplOpenGL3_Shutdown();
  ImGui_ImplSDL2_Shutdown();
  ImGui::DestroyContext();
  SDL_GL_DeleteContext(frame.gl_context);
  SDL_DestroyWindow(frame.window);
  SDL_Quit();
#endif
  return 0;
}
