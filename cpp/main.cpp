// Copyright (c) 2026 William Emerison Six -- GNU GPL v2 or later.
//
// Dear ImGui front-end for Towers of Hanoi, building native (SDL2 + OpenGL3)
// and, under Emscripten, as WebAssembly. At feature parity with the canonical
// Python per the UI-independent feature spec (tasks/reference/feature-spec.md):
// a menubar (Game / Relabel / Help), the board coloured by LABEL with the
// physical 1,2,3 reference shown when relabelled, all legal moves in the
// current labels with distinct rejection reasons, the optimal 2^N-1 target, win
// detection, and the full recipe feature set -- view / apply (recording the
// applied moves) / save-when-won (overwrite reported) -- with the three-panel
// rebinding view (recipe moves | rebinding label->peg | rebound physical moves)
// shown on invoke under a non-default labelling. Game logic is the ported
// engine (src/*.hpp), kept in sync with the Python behaviour oracle.

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
#include <cfloat>
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

// The physical peg pairs, in canonical order, paralleling model.move_options().
constexpr std::array<std::array<int, 2>, 6> kPegPairs{
    {{0, 1}, {0, 2}, {1, 0}, {1, 2}, {2, 0}, {2, 1}}};

// 2^n - 1, the optimal move count (presenter/engine min_moves).
int optimal_moves(int n) { return (1 << n) - 1; }

// A snapshot of a recipe/move invocation, rendered as the three-panel rebinding
// view. Captured at invoke time (with the labelling then active) so it stays a
// stable snapshot even if the user relabels afterward -- mirrors the Python wx
// dialog.
struct RecipeView {
  bool active = false;
  std::string title;
  std::string left_header;
  std::vector<std::array<int, 2>> moves;
  hanoi::Labelling labelling = hanoi::Labelling::OneTwoThree;
};

// The whole app state.
struct App {
  hanoi::Game game{3};
  hanoi::Labelling labelling = hanoi::Labelling::OneTwoThree;
  hanoi::Recorder recorder;
  hanoi::RecipeRegistry registry;
  char name_buf[64] = "";
  std::string status;        // last action / feedback message
  int recipe_sel = -1;       // selected index into registry.names()
  RecipeView view;           // the three-panel rebinding snapshot
  bool open_save = false;    // request to open the save-recipe modal
  bool open_help = false;    // request to open the help popup
  std::string illegal_msg;   // pending illegal-move reason (-> popup)
  bool open_illegal = false; // request to open the illegal-move popup
  bool want_quit = false;    // native: exit the loop

  void new_game(int n) {
    game = hanoi::Game(n);
    recorder.reset();
    status.clear();
    view.active = false;
  }

  // Apply a physical move and record it in default-label space (from_peg+1,
  // to_peg+1) -- so a typed move and a replayed move both land in the recorder,
  // exactly as the Python engine does.
  void do_move(const hanoi::Move &m) {
    game.apply(m);
    recorder.record(m.from_peg + 1, m.to_peg + 1);
  }

  [[nodiscard]] bool won() const { return game.check_win_condition(); }
};

// The reason a physical move is illegal, in the player's labels -- mirrors the
// Python engine._handle_move messages (empty source / larger-on-smaller).
std::string illegal_reason(const hanoi::Game &g, int fp, int tp, int from_label,
                           int to_label) {
  (void)to_label;
  if (g.towers()[static_cast<std::size_t>(fp)].empty()) {
    return "Peg " + std::to_string(from_label) + " is empty - nothing to move.";
  }
  if (!g.towers()[static_cast<std::size_t>(tp)].empty() &&
      g.towers()[static_cast<std::size_t>(fp)].back() >
          g.towers()[static_cast<std::size_t>(tp)].back()) {
    return "Can't put disc " +
           std::to_string(g.towers()[static_cast<std::size_t>(fp)].back()) +
           " on disc " +
           std::to_string(g.towers()[static_cast<std::size_t>(tp)].back()) +
           " - larger on smaller.";
  }
  return "Invalid move.";
}

// Draw the three pegs (coloured by label) + disks; when relabelled, a second
// label row shows the physical 1,2,3 reference under the active labels.
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
  const bool relabelled = app.labelling != hanoi::Labelling::OneTwoThree;

  for (int peg = 0; peg < 3; ++peg) {
    const float cx = origin.x + peg_gap * (static_cast<float>(peg) + 0.5f);
    const int label = hanoi::change_labels_on_pegs(app.labelling, peg);
    const ImU32 peg_col = kLabelColors[static_cast<std::size_t>(label)];
    dl->AddLine(ImVec2(cx, base_y), ImVec2(cx, origin.y + 12.0f), peg_col,
                5.0f);
    const std::vector<int> &stack =
        game.towers()[static_cast<std::size_t>(peg)];
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
    // Active label under the peg, in the label's colour.
    const float lx = cx - 4.0f;
    char lbl[2] = {static_cast<char>('1' + label), '\0'};
    dl->AddText(ImVec2(lx, base_y + 6.0f), peg_col, lbl);
    // Physical 1,2,3 reference row, only when relabelled (muted), so the
    // student sees both the current labels and the fixed physical pegs beneath.
    if (relabelled) {
      char phys[2] = {static_cast<char>('1' + peg), '\0'};
      dl->AddText(ImVec2(lx, base_y + 24.0f), IM_COL32(150, 150, 155, 255),
                  phys);
    }
  }
  ImGui::Dummy(ImVec2(board_w, board_h + (relabelled ? 46.0f : 32.0f)));
}

// The three-panel rebinding view: recipe/move labels (left) | label->peg key
// (middle) | rebound physical pegs (right). Under the default labelling there
// is no rebinding, so just the move list is shown.
void draw_recipe_view(App &app) {
  if (!app.view.active) {
    return;
  }
  ImGui::Separator();
  ImGui::TextUnformatted(app.view.title.c_str());
  const bool relabelled = app.view.labelling != hanoi::Labelling::OneTwoThree;
  if (!relabelled) {
    ImGui::TextDisabled(
        "(default labelling -- no rebinding; the recipe's moves are the "
        "physical moves)");
    for (std::size_t i = 0; i < app.view.moves.size(); ++i) {
      ImGui::Text("%zu: %d -> %d", i + 1, app.view.moves[i][0],
                  app.view.moves[i][1]);
    }
  } else if (ImGui::BeginTable("rebinding", 3,
                               ImGuiTableFlags_Borders |
                                   ImGuiTableFlags_SizingStretchProp)) {
    ImGui::TableSetupColumn(app.view.left_header.c_str());
    ImGui::TableSetupColumn("Rebinding (label -> peg)");
    ImGui::TableSetupColumn("Rebound (physical pegs)");
    ImGui::TableHeadersRow();
    const std::array<std::array<int, 2>, 3> key =
        hanoi::rebinding(app.view.labelling);
    const std::vector<std::array<int, 2>> rebound =
        hanoi::rebound_moves(app.view.moves, app.view.labelling);
    const std::size_t rows = app.view.moves.size();
    for (std::size_t i = 0; i < rows; ++i) {
      ImGui::TableNextRow();
      ImGui::TableSetColumnIndex(0);
      ImGui::Text("%zu: %d -> %d", i + 1, app.view.moves[i][0],
                  app.view.moves[i][1]);
      ImGui::TableSetColumnIndex(1);
      if (i < key.size()) {
        ImGui::Text("label %d -> peg %d", key[i][0], key[i][1]);
      }
      ImGui::TableSetColumnIndex(2);
      ImGui::Text("%zu: %d -> %d", i + 1, rebound[i][0], rebound[i][1]);
    }
    // If there are fewer moves than the 3 key rows, show the remaining key
    // rows.
    for (std::size_t i = rows; i < key.size(); ++i) {
      ImGui::TableNextRow();
      ImGui::TableSetColumnIndex(1);
      ImGui::Text("label %d -> peg %d", key[i][0], key[i][1]);
    }
    ImGui::EndTable();
  }
  if (ImGui::SmallButton("Dismiss##view")) {
    app.view.active = false;
  }
}

// Open the three-panel snapshot for a set of moves under the current labelling.
void open_view(App &app, const std::string &title,
               const std::string &left_header,
               const std::vector<std::array<int, 2>> &moves) {
  app.view.active = true;
  app.view.title = title;
  app.view.left_header = left_header;
  app.view.moves = moves;
  app.view.labelling = app.labelling;
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
#ifndef __EMSCRIPTEN__
    // A browser tab has no app-driven quit; native gets an explicit Quit.
    ImGui::Separator();
    if (ImGui::MenuItem("Quit")) {
      app.want_quit = true;
    }
#endif
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
  if (ImGui::BeginMenu("Help")) {
    if (ImGui::MenuItem("Controls / About")) {
      app.open_help = true;
    }
    ImGui::EndMenu();
  }
  ImGui::EndMenuBar();
}

// The save-recipe modal (name input). Reached only when the game is won.
void draw_save_modal(App &app) {
  if (app.open_save) {
    // Prefill the default name solve-<N> (N = disk count), matching the Python
    // wx GUI and feature-spec.md §4.5 -- the user accepts or edits it.
    std::snprintf(app.name_buf, sizeof(app.name_buf), "solve-%d",
                  app.game.num_disks());
    ImGui::OpenPopup("Save recipe");
    app.open_save = false;
  }
  if (ImGui::BeginPopupModal("Save recipe", nullptr,
                             ImGuiWindowFlags_AlwaysAutoResize)) {
    ImGui::TextUnformatted("Name this recipe:");
    ImGui::InputText("##name", app.name_buf, sizeof(app.name_buf));
    const bool has_name = app.name_buf[0] != '\0';
    if (ImGui::Button("Save") && has_name) {
      const std::string name = app.name_buf;
      const bool overwrote = app.registry.get(name) != nullptr;
      app.registry.save(app.recorder.to_recipe(name, app.game.num_disks()));
      app.status =
          (overwrote ? "Overwrote recipe '" : "Saved recipe '") + name + "'.";
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

void draw_help_modal(App &app) {
  if (app.open_help) {
    ImGui::OpenPopup("Controls / About");
    app.open_help = false;
  }
  if (ImGui::BeginPopupModal("Controls / About", nullptr,
                             ImGuiWindowFlags_AlwaysAutoResize)) {
    ImGui::TextUnformatted("Towers of Hanoi -- C++ / Dear ImGui");
    ImGui::Separator();
    ImGui::TextWrapped(
        "A teaching tool for solving Hanoi by hand: solve small, relabel the "
        "pegs, replay.\n\n"
        "- Game menu: start a new game (pick the disk count) or restart.\n"
        "- Relabel menu: rename the pegs (a permutation of 1,2,3). Disks don't "
        "move; colour follows the LABEL.\n"
        "- Move buttons: move the top disk between pegs, in the CURRENT "
        "labels. "
        "An illegal move explains why.\n"
        "- Recipes: Save a solved game as a named recipe (after you win). "
        "View a recipe's moves, or Apply it under the current labelling -- "
        "when relabelled, you see the three-panel rebinding "
        "(recipe moves | label->peg | rebound to physical pegs).\n\n"
        "The goal peg is physical peg 3. Optimal solution: 2^N - 1 moves.");
    ImGui::Separator();
    if (ImGui::Button("Close")) {
      ImGui::CloseCurrentPopup();
    }
    ImGui::EndPopup();
  }
}

void draw_illegal_modal(App &app) {
  if (app.open_illegal) {
    ImGui::OpenPopup("Illegal move");
    app.open_illegal = false;
  }
  // A min width so a one-line reason ("Can't put disc 3 on disc 2 -- larger on
  // smaller.") isn't wrapped into a cramped, too-narrow column.
  ImGui::SetNextWindowSizeConstraints(ImVec2(360.0f, 0.0f),
                                      ImVec2(620.0f, FLT_MAX));
  if (ImGui::BeginPopupModal("Illegal move", nullptr,
                             ImGuiWindowFlags_AlwaysAutoResize)) {
    ImGui::TextWrapped("%s", app.illegal_msg.c_str());
    if (ImGui::Button("OK")) {
      ImGui::CloseCurrentPopup();
    }
    ImGui::EndPopup();
  }
}

// The move buttons: all six are ALWAYS shown in a fixed layout (so they never
// jump), in the current labels. Illegal moves are GRAYED (muted button + text
// colours) so they read as unavailable, but stay clickable so a click still
// pops a dialog with the distinct reason (empty source / larger-on-smaller); a
// legal one is applied + recorded.
void draw_moves(App &app) {
  ImGui::Separator();
  ImGui::TextUnformatted("Moves (current labels):");
  std::array<bool, 9> legal{};
  for (const hanoi::Move &m : app.game.move_options()) {
    legal[static_cast<std::size_t>(m.from_peg * 3 + m.to_peg)] = true;
  }
  const bool won = app.won();
  for (const std::array<int, 2> &pair : kPegPairs) {
    const int fp = pair[0];
    const int tp = pair[1];
    const int from_label = hanoi::change_labels_on_pegs(app.labelling, fp) + 1;
    const int to_label = hanoi::change_labels_on_pegs(app.labelling, tp) + 1;
    char btn[24];
    std::snprintf(btn, sizeof(btn), "%d -> %d##%d%d", from_label, to_label, fp,
                  tp);
    const bool is_legal = !won && legal[static_cast<std::size_t>(fp * 3 + tp)];
    if (!is_legal) {
      ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(0.30f, 0.30f, 0.33f, 1.0f));
      ImGui::PushStyleColor(ImGuiCol_ButtonHovered,
                            ImVec4(0.38f, 0.38f, 0.42f, 1.0f));
      ImGui::PushStyleColor(ImGuiCol_ButtonActive,
                            ImVec4(0.30f, 0.30f, 0.33f, 1.0f));
      ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.60f, 0.60f, 0.63f, 1.0f));
    }
    if (ImGui::Button(btn)) {
      if (won) {
        app.illegal_msg = "The game is already solved - start a new game.";
        app.open_illegal = true;
      } else if (legal[static_cast<std::size_t>(fp * 3 + tp)]) {
        const bool relabelled = app.labelling != hanoi::Labelling::OneTwoThree;
        app.do_move(hanoi::Move{fp, tp});
        app.status = "Moved " + std::to_string(from_label) + " -> " +
                     std::to_string(to_label) + ".";
        // Teaching step: under a relabelling, show the single move's rebinding.
        if (relabelled) {
          open_view(app, "Rebinding for your move", "Your move",
                    {{{from_label, to_label}}});
        }
        if (app.won()) {
          const int mm = optimal_moves(app.game.num_disks());
          const int mv = app.game.current_moves();
          const std::string verdict =
              mv == mm ? "Optimal!"
                       : std::to_string(mv - mm) + " more than the minimum (" +
                             std::to_string(mm) + ").";
          app.status = "Solved in " + std::to_string(mv) + " moves - " +
                       verdict + "  Save it as a recipe to keep it.";
        }
      } else {
        app.illegal_msg =
            illegal_reason(app.game, fp, tp, from_label, to_label);
        app.open_illegal = true;
      }
    }
    if (!is_legal) {
      ImGui::PopStyleColor(4);
    }
    ImGui::SameLine();
  }
  ImGui::NewLine();
}

// The recipes panel: the saved list (name + disk/move counts), View / Apply,
// Save (only when won) and Reset recording.
void draw_recipes(App &app) {
  ImGui::Separator();
  ImGui::Text("Recipes  (recording: %zu moves)", app.recorder.moves().size());

  const std::vector<std::string> names = app.registry.names();
  if (app.recipe_sel >= static_cast<int>(names.size())) {
    app.recipe_sel = -1;
  }
  if (ImGui::BeginListBox("##recipes", ImVec2(-FLT_MIN, 120))) {
    for (int i = 0; i < static_cast<int>(names.size()); ++i) {
      const hanoi::Recipe *r =
          app.registry.get(names[static_cast<std::size_t>(i)]);
      char row[128];
      std::snprintf(row, sizeof(row), "%s  (%d discs, %zu moves)",
                    names[static_cast<std::size_t>(i)].c_str(),
                    r != nullptr ? r->disk_count : 0,
                    r != nullptr ? r->default_moves.size() : 0);
      if (ImGui::Selectable(row, app.recipe_sel == i)) {
        app.recipe_sel = i;
      }
    }
    ImGui::EndListBox();
  }

  const bool has_sel =
      app.recipe_sel >= 0 && app.recipe_sel < static_cast<int>(names.size());
  const std::string sel_name =
      has_sel ? names[static_cast<std::size_t>(app.recipe_sel)] : std::string();

  ImGui::BeginDisabled(!has_sel);
  if (ImGui::Button("View")) {
    const hanoi::Recipe *r = app.registry.get(sel_name);
    if (r != nullptr) {
      open_view(app, "Recipe '" + sel_name + "'", "Recipe moves",
                r->default_moves);
    }
  }
  ImGui::SameLine();
  if (ImGui::Button("Apply")) {
    const hanoi::Recipe *r = app.registry.get(sel_name);
    if (r != nullptr) {
      const bool relabelled = app.labelling != hanoi::Labelling::OneTwoThree;
      const std::vector<hanoi::StepResult> res =
          hanoi::apply(*r, app.game, app.labelling);
      int applied = 0;
      std::string err;
      for (const hanoi::StepResult &s : res) {
        if (s.ok()) {
          ++applied;
          // Record the applied move in default-label space (like the Python
          // engine), so a replayed solution is itself saveable.
          app.recorder.record(*s.from_peg + 1, *s.to_peg + 1);
        } else {
          err = *s.error;
        }
      }
      app.status = "Applied '" + sel_name + "': " + std::to_string(applied) +
                   "/" + std::to_string(r->default_moves.size()) + " moves" +
                   (err.empty() ? "." : " - stopped: " + err);
      if (relabelled) {
        open_view(app, "Rebinding for '" + sel_name + "'", "Recipe moves",
                  r->default_moves);
      }
      if (app.won()) {
        const int mm = optimal_moves(app.game.num_disks());
        const int mv = app.game.current_moves();
        app.status += (mv == mm)
                          ? "  Solved - optimal!"
                          : "  Solved in " + std::to_string(mv) +
                                " moves (min " + std::to_string(mm) + ").";
      }
    }
  }
  ImGui::EndDisabled();

  ImGui::SameLine();
  // Save the current recording -- only meaningful after a win (spec: save is
  // post-win), and the overwrite is reported in the modal's result.
  ImGui::BeginDisabled(!app.won() || app.recorder.moves().empty());
  if (ImGui::Button("Save current solution")) {
    app.open_save = true;
  }
  ImGui::EndDisabled();
  ImGui::SameLine();
  ImGui::BeginDisabled(app.recorder.moves().empty());
  if (ImGui::Button("Reset recording")) {
    app.recorder.reset();
    app.status = "Recording reset.";
  }
  ImGui::EndDisabled();
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
  draw_help_modal(app);
  draw_illegal_modal(app);

  ImGui::Text("Moves: %d   (optimal: %d)", app.game.current_moves(),
              optimal_moves(app.game.num_disks()));
  ImGui::SameLine();
  if (app.won()) {
    ImGui::TextColored(ImVec4(0.3f, 0.9f, 0.3f, 1.0f), "  -- solved!");
  }

  draw_board(app);
  draw_moves(app);
  draw_recipes(app);
  draw_recipe_view(app);

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
  if (f.app.want_quit) {
    f.done = true;
  }
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
                                  SDL_WINDOWPOS_CENTERED, 820, 640, flags);
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
