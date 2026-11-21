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
#include <cmath>
#include <cstddef>
#include <cstdio>
#include <optional>
#include <string>
#include <vector>

namespace {

// Blue / gold / red, indexed by 0-indexed LABEL (not physical peg) -- the peg
// colour tracks its label so the student keeps "label 1 is the blue peg" after
// relabelling.
const std::array<ImU32, 3> kLabelColors{IM_COL32(70, 130, 220, 255),
                                        IM_COL32(220, 190, 60, 255),
                                        IM_COL32(220, 80, 80, 255)};

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
  int selected = -1; // the selected move's row, or -1 for none
};

// The whole app state.
struct App {
  hanoi::Game game{3};
  hanoi::Labelling labelling = hanoi::Labelling::OneTwoThree;
  hanoi::Recorder recorder;
  hanoi::RecipeRegistry registry;
  char name_buf[64] = "";
  std::string status;        // last action / feedback message
  RecipeView view;           // the three-panel rebinding snapshot
  bool open_save = false;    // request to open the save-recipe modal
  bool open_help = false;    // request to open the help popup
  std::string illegal_msg;   // pending illegal-move reason (-> popup)
  bool open_illegal = false; // request to open the illegal-move popup
  bool want_quit = false;    // native: exit the loop
  bool won_once = false;     // Tier-2 unlock: latched at the first win, kept
  bool help_shown = false;   // first-run "How to Play" shown once
  bool open_win = false;     // request to open the first-win teaching modal
  std::vector<std::string> win_lines; // shared celebration lines (per win)
  // Save-on-discard (feature-spec §4.9; the win-celebration UX doc): whether
  // the current won solution was reached by replaying a recipe and whether it
  // was already saved; a New Game deferred behind the save-before-discard
  // modal.
  bool won_via_apply = false;
  bool saved_current = false;
  bool open_discard_save = false;
  int pending_new_game = -1;
  // Disc drag-drop (spike, mirrored across the GUIs): the physical peg whose
  // top disc is being dragged (-1 = none), its size, and the cursor position.
  int drag_src = -1;
  int drag_size = 0;
  float drag_x = 0.0f;
  float drag_y = 0.0f;
  // History review (clicking a history row): how many moves the board shows
  // (-1 = the live game) and the board after them. A move or apply made while
  // reviewing waits (pending_*) on the "Continue from here?" modal.
  int review = -1;
  std::optional<hanoi::Game> review_game;
  int pending_fp = -1;
  int pending_tp = -1;
  std::string pending_apply;
  bool open_continue = false;
  int pending_from = 0; // the keyboard move's typed from-peg, 0 = none

  void new_game(int n) {
    game = hanoi::Game(n);
    recorder.reset();
    review = -1;
    review_game.reset();
    clear_pending();
    status.clear();
    view.active = false;
    open_win = false;
    win_lines.clear();
    won_via_apply = false;
    saved_current = false;
    open_discard_save = false;
    pending_new_game = -1;
  }

  // Apply a physical move and record it in default-label space (from_peg+1,
  // to_peg+1) -- so a typed move and a replayed move both land in the recorder,
  // exactly as the Python engine does.
  void do_move(const hanoi::Move &m) {
    game.apply(m);
    recorder.record(m.from_peg + 1, m.to_peg + 1);
  }

  [[nodiscard]] bool won() const { return game.check_win_condition(); }

  // The game the board shows: the reviewed state, or the live game.
  [[nodiscard]] const hanoi::Game &board() const {
    return review_game ? *review_game : game;
  }
  [[nodiscard]] bool has_pending() const {
    return pending_fp >= 0 || !pending_apply.empty();
  }
  void clear_pending() {
    pending_fp = -1;
    pending_tp = -1;
    pending_apply.clear();
  }

  // Review the board as it was after the first `count` moves; the last move is
  // the live game, so it leaves review.
  void review_move(int count) {
    const int total = static_cast<int>(recorder.moves().size());
    if (count >= total) {
      review = -1;
      review_game.reset();
      status.clear();
      return;
    }
    const std::vector<std::array<int, 2>> first(
        recorder.moves().begin(),
        recorder.moves().begin() + static_cast<std::ptrdiff_t>(count));
    review = count;
    review_game = hanoi::replay_default_moves(game.num_disks(), first);
    status = "Reviewing move " + std::to_string(count) + " of " +
             std::to_string(total) +
             ". Make a move to continue from here, or Back to current.";
  }

  // Continue from the reviewed move: the live game becomes the reviewed board
  // and every later move is deleted.
  void continue_from_review() {
    if (review < 0 || !review_game) {
      return;
    }
    game = *review_game;
    recorder.truncate(static_cast<std::size_t>(review));
    review = -1;
    review_game.reset();
    // The game changed, so a saved or replayed win no longer describes it.
    saved_current = false;
    won_via_apply = false;
  }
};

// On a win, capture the shared celebration lines and request the modal (shown
// once per win by draw_win_modal). The recipe teaching (first_win) keys off the
// won_once latch, read before the frame's draw latches it. No-op when not won.
void trigger_win(App &app) {
  if (!app.won()) {
    return;
  }
  const bool first_win = !app.won_once;
  app.win_lines = hanoi::format_win_celebration(
      app.game.num_disks(), app.game.current_moves(),
      optimal_moves(app.game.num_disks()), first_win);
  if (!app.win_lines.empty()) {
    app.status = app.win_lines.front();
  }
  // First win: a teaching modal (never collides with the §4.8 rebinding view,
  // as the first win is always a clean default-label solve). Later wins: the
  // status line above only; the save is offered at the New Game boundary.
  if (first_win) {
    app.open_win = true;
  }
}

// New Game / New Game (Same Size): if the finished game was won by hand and not
// yet saved, defer to the save-before-discard modal; else start immediately.
void request_new_game(App &app, int n) {
  if (app.won() && !app.won_via_apply && !app.saved_current) {
    app.pending_new_game = n;
    app.open_discard_save = true;
  } else {
    app.new_game(n);
  }
}

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

// Dispatch a physical from->to move (shared by the keyboard move and disc
// drag-drop). Defined after open_view; forward-declared here for draw_board.
void do_board_move(App &app, int fp, int tp);

// Draw the three pegs (coloured by label) + disks; when relabelled, a second
// label row shows the physical 1,2,3 reference under the active labels.
void draw_board(App &app) {
  const hanoi::Game &game = app.board();
  ImDrawList *dl = ImGui::GetWindowDrawList();
  const ImVec2 origin = ImGui::GetCursorScreenPos();
  const float board_w = ImGui::GetContentRegionAvail().x;
  const float board_h = 260.0f;
  // Match the egui + wxPython boards: a fixed edge margin, then three equal
  // peg zones across the remaining width, so the outer pegs (and the widest
  // discs) don't hug the board edges and all three graphical boards share one
  // layout. The centres were already evenly spaced; the ImGui board uniquely
  // lacked this margin, so its outer pegs sat flush to the edges.
  const float margin = 20.0f;
  const float inner_w = board_w - 2.0f * margin;
  const float avail_w = inner_w > 80.0f ? inner_w : 80.0f;
  const float peg_gap = avail_w / 3.0f;
  const float base_y = origin.y + board_h;
  const float disk_h = 20.0f;
  const float max_disk_w = peg_gap * 0.9f;
  const int n = game.num_disks() > 0 ? game.num_disks() : 1;
  const bool relabelled = app.labelling != hanoi::Labelling::OneTwoThree;
  const float extra = relabelled ? 46.0f : 32.0f;

  std::array<float, 3> cx{};
  for (int peg = 0; peg < 3; ++peg) {
    cx[static_cast<std::size_t>(peg)] =
        origin.x + margin + peg_gap * (static_cast<float>(peg) + 0.5f);
  }

  // Disc drag-drop (spike, mirrored across the GUIs): an invisible button over
  // the board owns the gesture while the draw list paints over it. Press picks
  // up the top disc of the nearest peg; the disc follows the cursor; release
  // drops onto the nearest peg (forgiving) and dispatches through the same
  // do_board_move the keyboard move uses. Dragging is off once the game is
  // won. Mirrors the wxPython GraphicsBoardRenderer.
  ImGui::InvisibleButton("##board", ImVec2(board_w, board_h + extra));
  const auto nearest_peg = [&](float x) -> int {
    int best = 0;
    for (int i = 1; i < 3; ++i) {
      if (std::fabs(x - cx[static_cast<std::size_t>(i)]) <
          std::fabs(x - cx[static_cast<std::size_t>(best)])) {
        best = i;
      }
    }
    return best;
  };
  if (game.check_win_condition() || app.has_pending()) {
    app.drag_src = -1; // dragging is off once solved, and while asking
  } else {
    const ImVec2 mp = ImGui::GetMousePos();
    if (ImGui::IsItemActivated()) {
      const int peg = nearest_peg(mp.x);
      const std::vector<int> &stack =
          game.towers()[static_cast<std::size_t>(peg)];
      if (!stack.empty()) {
        app.drag_src = peg;
        app.drag_size = stack.back();
      }
    }
    if (ImGui::IsItemActive() && app.drag_src >= 0) {
      app.drag_x = mp.x;
      app.drag_y = mp.y;
    }
    if (ImGui::IsItemDeactivated() && app.drag_src >= 0) {
      const int src = app.drag_src;
      const int target = nearest_peg(mp.x);
      app.drag_src = -1;
      if (target != src) {
        do_board_move(app, src, target);
      }
    }
  }

  for (int peg = 0; peg < 3; ++peg) {
    const float pcx = cx[static_cast<std::size_t>(peg)];
    const int label = hanoi::change_labels_on_pegs(app.labelling, peg);
    const ImU32 peg_col = kLabelColors[static_cast<std::size_t>(label)];
    dl->AddLine(ImVec2(pcx, base_y), ImVec2(pcx, origin.y + 12.0f), peg_col,
                5.0f);
    const std::vector<int> &stack =
        game.towers()[static_cast<std::size_t>(peg)];
    for (std::size_t level = 0; level < stack.size(); ++level) {
      // Omit the disc currently being dragged from its home peg.
      if (app.drag_src == peg && level == stack.size() - 1) {
        continue;
      }
      const int size = stack[level];
      const float w =
          max_disk_w * (static_cast<float>(size) / static_cast<float>(n));
      const float y = base_y - disk_h * (static_cast<float>(level) + 1.0f);
      const ImVec2 a(pcx - w / 2.0f, y);
      const ImVec2 b(pcx + w / 2.0f, y + disk_h - 3.0f);
      dl->AddRectFilled(a, b, IM_COL32(210, 210, 215, 255), 4.0f);
      dl->AddRect(a, b, IM_COL32(30, 30, 40, 255), 4.0f);
    }
    // Active label under the peg, in the label's colour.
    const float lx = pcx - 4.0f;
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

  // The dragged disc follows the cursor, drawn on top (a gold tint signals the
  // picked-up disc).
  if (app.drag_src >= 0) {
    const float w = max_disk_w *
                    (static_cast<float>(app.drag_size) / static_cast<float>(n));
    const ImVec2 a(app.drag_x - w / 2.0f, app.drag_y - disk_h / 2.0f);
    const ImVec2 b(app.drag_x + w / 2.0f, app.drag_y + disk_h / 2.0f - 3.0f);
    dl->AddRectFilled(a, b, IM_COL32(235, 225, 150, 255), 4.0f);
    dl->AddRect(a, b, IM_COL32(60, 55, 30, 255), 4.0f);
  }
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
    // One table, so the three columns scroll together. Clicking a move row
    // selects it across all columns, and the key marks (with an arrowhead) the
    // two label->peg bindings that move uses (">": the default ImGui font has
    // no arrowhead glyph).
    auto key_cell = [&app, &key](std::size_t i) {
      const int sel = app.view.selected;
      const bool used =
          sel >= 0 &&
          (app.view.moves[static_cast<std::size_t>(sel)][0] == key[i][0] ||
           app.view.moves[static_cast<std::size_t>(sel)][1] == key[i][0]);
      ImGui::Text("%s label %d -> peg %d", used ? ">" : " ", key[i][0],
                  key[i][1]);
    };
    for (std::size_t i = 0; i < rows; ++i) {
      ImGui::TableNextRow();
      ImGui::TableSetColumnIndex(0);
      char label[32];
      std::snprintf(label, sizeof label, "%zu: %d -> %d##move%zu", i + 1,
                    app.view.moves[i][0], app.view.moves[i][1], i);
      if (ImGui::Selectable(label, app.view.selected == static_cast<int>(i),
                            ImGuiSelectableFlags_SpanAllColumns)) {
        app.view.selected = static_cast<int>(i);
      }
      ImGui::TableSetColumnIndex(1);
      if (i < key.size()) {
        key_cell(i);
      }
      ImGui::TableSetColumnIndex(2);
      ImGui::Text("%zu: %d -> %d", i + 1, rebound[i][0], rebound[i][1]);
    }
    // If there are fewer moves than the 3 key rows, show the remaining key
    // rows.
    for (std::size_t i = rows; i < key.size(); ++i) {
      ImGui::TableNextRow();
      ImGui::TableSetColumnIndex(1);
      key_cell(i);
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
  app.view.selected = -1;
}

// Dispatch a physical from->to move -- shared by the keyboard move and a disc
// drag-drop so a dragged move and a typed move take one path (mirrors the
// wxPython _on_move). Illegal -> the distinct rejection reason in a popup;
// legal -> apply + record + status, the single-move rebinding under a
// relabelling, and the win verdict.
void do_board_move(App &app, int fp, int tp) {
  if (app.review >= 0) { // reviewing: ask first (draw_continue_modal)
    app.pending_fp = fp;
    app.pending_tp = tp;
    app.open_continue = true;
    return;
  }
  const int from_label = hanoi::change_labels_on_pegs(app.labelling, fp) + 1;
  const int to_label = hanoi::change_labels_on_pegs(app.labelling, tp) + 1;
  if (app.won()) {
    app.illegal_msg = "The game is already solved - start a new game.";
    app.open_illegal = true;
    return;
  }
  bool legal = false;
  for (const hanoi::Move &m : app.game.move_options()) {
    if (m.from_peg == fp && m.to_peg == tp) {
      legal = true;
      break;
    }
  }
  if (!legal) {
    app.illegal_msg = illegal_reason(app.game, fp, tp, from_label, to_label);
    app.open_illegal = true;
    return;
  }
  const bool relabelled = app.labelling != hanoi::Labelling::OneTwoThree;
  app.do_move(hanoi::Move{fp, tp});
  app.status = "Moved " + std::to_string(from_label) + " -> " +
               std::to_string(to_label) + ".";
  if (relabelled) {
    open_view(app, "Rebinding for your move", "Your move",
              {{{from_label, to_label}}});
  }
  trigger_win(app);
}

// View a saved recipe (Recipe menu -> <name> -> View): under a relabelling the
// three-panel rebinding view (recipe moves | label->peg | rebound pegs), else
// just the recipe's moves. Mirrors the wxPython oracle's _view_recipe.
void view_recipe(App &app, const std::string &name) {
  const hanoi::Recipe *r = app.registry.get(name);
  if (r == nullptr) {
    return;
  }
  open_view(app, "Recipe '" + name + "'", "Recipe moves", r->default_moves);
}

// Apply a saved recipe under the current labelling (Recipe menu -> <name> ->
// Apply): replay + record each move, show the rebinding view when relabelled,
// and summarise to the status line. Mirrors the oracle's _apply_recipe_by_name.
void apply_recipe(App &app, const std::string &name) {
  const hanoi::Recipe *r = app.registry.get(name);
  if (r == nullptr) {
    return;
  }
  if (app.review >= 0) { // reviewing: ask first (draw_continue_modal)
    app.pending_apply = name;
    app.open_continue = true;
    return;
  }
  const bool relabelled = app.labelling != hanoi::Labelling::OneTwoThree;
  const std::vector<hanoi::StepResult> res =
      hanoi::apply(*r, app.game, app.labelling);
  int applied = 0;
  std::string err;
  for (const hanoi::StepResult &s : res) {
    if (s.ok()) {
      ++applied;
      app.recorder.record(*s.from_peg + 1, *s.to_peg + 1);
    } else {
      err = *s.error;
    }
  }
  app.status = "Applied '" + name + "': " + std::to_string(applied) + "/" +
               std::to_string(r->default_moves.size()) + " moves" +
               (err.empty() ? "." : " - stopped: " + err);
  if (relabelled) {
    open_view(app, "Rebinding for '" + name + "'", "Recipe moves",
              r->default_moves);
  }
  trigger_win(app);
  if (app.won()) {
    app.won_via_apply = true;
  }
}

void draw_menubar(App &app) {
  if (!ImGui::BeginMenuBar()) {
    return;
  }
  if (ImGui::BeginMenu("Game")) {
    // New Game picks a disc count (1-10, matching the wx front-ends);
    // New Game (Same Size) restarts at the current count.
    if (ImGui::BeginMenu("New Game")) {
      for (int n = 1; n <= 10; ++n) {
        const std::string item = std::to_string(n) + " disks";
        if (ImGui::MenuItem(item.c_str(), nullptr, app.game.num_disks() == n)) {
          request_new_game(app, n);
        }
      }
      ImGui::EndMenu();
    }
    if (ImGui::MenuItem("New Game (Same Size)")) {
      request_new_game(app, app.game.num_disks());
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
  // Tier-2 (feature-spec §3.5): Relabel + Recipe are gated until the first win,
  // then stay enabled for the session (dim, don't remove).
  ImGui::BeginDisabled(!app.won_once);
  if (ImGui::BeginMenu("Relabel")) {
    for (const hanoi::Labelling l : hanoi::kAllLabellings) {
      if (ImGui::MenuItem(hanoi::labelling_name(l), nullptr,
                          app.labelling == l)) {
        app.labelling = l;
      }
    }
    ImGui::EndMenu();
  }
  // Tier-3: recipes live in a menu, not the main workspace. "Save current
  // solution" first; then each saved recipe is a submenu -> View / Apply
  // (point at the recipe, not an abstract verb). Matches the wxPython oracle.
  if (ImGui::BeginMenu("Recipe")) {
    if (ImGui::MenuItem("Save current solution", nullptr, false,
                        app.won() && !app.recorder.moves().empty())) {
      app.open_save = true;
    }
    if (ImGui::MenuItem("Reset recording", nullptr, false,
                        !app.recorder.moves().empty())) {
      app.recorder.reset();
      app.status = "Recording reset.";
    }
    ImGui::Separator();
    const std::vector<std::string> recipe_names = app.registry.names();
    if (recipe_names.empty()) {
      ImGui::MenuItem("(no saved recipes yet)", nullptr, false, false);
    } else {
      for (const std::string &name : recipe_names) {
        const hanoi::Recipe *r = app.registry.get(name);
        char label[128];
        std::snprintf(label, sizeof(label), "%s  (%d discs, %zu moves)",
                      name.c_str(), r != nullptr ? r->disk_count : 0,
                      r != nullptr ? r->default_moves.size() : 0);
        if (ImGui::BeginMenu(label)) {
          if (ImGui::MenuItem("View")) {
            view_recipe(app, name);
          }
          if (ImGui::MenuItem("Apply")) {
            apply_recipe(app, name);
          }
          ImGui::EndMenu();
        }
      }
    }
    ImGui::EndMenu();
  }
  ImGui::EndDisabled();
  if (ImGui::BeginMenu("Help")) {
    if (ImGui::MenuItem("How to Play")) {
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
      app.saved_current = true;
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

// The first-win teaching modal (the teaching hinge, feature-spec §4.9): the
// shared lines (congrats + result + the recipe teaching), dismissed with "Got
// it". No Save here -- the save is offered at the New Game boundary. Shown only
// on the first win, which is always a clean default-label solve, so it never
// collides with the §4.8 rebinding view. Requested by trigger_win().
void draw_win_modal(App &app) {
  if (app.open_win) {
    ImGui::OpenPopup("You solved it!");
    app.open_win = false;
  }
  ImGui::SetNextWindowPos(ImGui::GetMainViewport()->GetCenter(),
                          ImGuiCond_Appearing, ImVec2(0.5f, 0.5f));
  if (ImGui::BeginPopupModal("You solved it!", nullptr,
                             ImGuiWindowFlags_AlwaysAutoResize)) {
    for (const std::string &line : app.win_lines) {
      ImGui::TextUnformatted(line.c_str());
    }
    ImGui::Separator();
    if (ImGui::Button("Got it")) {
      ImGui::CloseCurrentPopup();
    }
    ImGui::EndPopup();
  }
}

// The save-before-discard modal: a New Game requested while a hand-won, unsaved
// solution is on the board asks whether to save it as "solve-<N>" first (the
// save-before-you-close pattern; the win-celebration UX doc), then starts the
// pending new game either way. Requested by request_new_game().
void draw_discard_save_modal(App &app) {
  if (app.open_discard_save) {
    ImGui::OpenPopup("Save solution?");
    app.open_discard_save = false;
  }
  ImGui::SetNextWindowPos(ImGui::GetMainViewport()->GetCenter(),
                          ImGuiCond_Appearing, ImVec2(0.5f, 0.5f));
  if (ImGui::BeginPopupModal("Save solution?", nullptr,
                             ImGuiWindowFlags_AlwaysAutoResize)) {
    ImGui::TextUnformatted(
        "Save your solution as a recipe before starting over?");
    ImGui::Separator();
    bool decided = false;
    if (ImGui::Button("Save")) {
      const std::string name = hanoi::default_recipe_name(app.game.num_disks());
      app.registry.save(app.recorder.to_recipe(name, app.game.num_disks()));
      decided = true;
    }
    ImGui::SameLine();
    if (ImGui::Button("Don't save")) {
      decided = true;
    }
    if (decided) {
      const int n = app.pending_new_game >= 1 ? app.pending_new_game : 3;
      app.new_game(n); // resets pending_new_game + the save flags
      ImGui::CloseCurrentPopup();
    }
    ImGui::EndPopup();
  }
}

void draw_help_modal(App &app) {
  if (app.open_help) {
    ImGui::OpenPopup("How to Play");
    app.open_help = false;
  }
  // Center the popup on the viewport and give it a comfortable fixed width (the
  // wrapped text then fills it); without this it opened off-center and too
  // narrow. Height stays auto. Matches the egui/Tauri centered How-to-Play.
  ImGui::SetNextWindowPos(ImGui::GetMainViewport()->GetCenter(),
                          ImGuiCond_Appearing, ImVec2(0.5f, 0.5f));
  ImGui::SetNextWindowSize(ImVec2(520.0f, 0.0f), ImGuiCond_Appearing);
  if (ImGui::BeginPopupModal("How to Play", nullptr, ImGuiWindowFlags_None)) {
    ImGui::TextUnformatted("How to Play -- Towers of Hanoi");
    ImGui::Separator();
    ImGui::TextWrapped(
        "Goal: move the whole stack of disks onto physical peg 3.\n"
        "  - Move one disk at a time (the top disk of a peg).\n"
        "  - Never place a larger disk on a smaller one.\n\n"
        "The method this teaches: solve a SMALL stack, then RELABEL the pegs "
        "to "
        "reuse that solution for a bigger stack -- \"solve small, relabel, "
        "replay.\" Relabelling and recipes unlock after your first win.\n\n"
        "- Drag a disk, or type the from-peg number then the to-peg number: "
        "move the top disk between pegs, in the CURRENT labels. An illegal "
        "move explains why.\n"
        "- Relabel menu: rename the pegs (a permutation of 1,2,3). Disks don't "
        "move; colour follows the LABEL.\n"
        "- Recipe menu: Save a solved game, then View or Apply it under the "
        "current labelling -- when relabelled, you see the three-panel "
        "rebinding (recipe moves | label->peg | rebound to physical pegs).\n\n"
        "Optimal solution: 2^N - 1 moves.");
    ImGui::Separator();
    if (ImGui::Button("Got it")) {
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

// How to move: drag a disc on the board, or the keyboard move -- type the
// from-peg number, then the to-peg number; Esc cancels (ui-design-principles
// ruling 7; there are no move buttons). The keys go through do_board_move, the
// same checked path as a drop, so an illegal pair pops up its reason.
void draw_moves(App &app) {
  ImGui::Separator();
  const ImGuiIO &io = ImGui::GetIO();
  if (!io.WantCaptureKeyboard &&
      !ImGui::IsPopupOpen("", ImGuiPopupFlags_AnyPopupId)) {
    static constexpr std::array<std::array<ImGuiKey, 2>, 3> kPegKeys{
        {{ImGuiKey_1, ImGuiKey_Keypad1},
         {ImGuiKey_2, ImGuiKey_Keypad2},
         {ImGuiKey_3, ImGuiKey_Keypad3}}};
    for (std::size_t i = 0; i < kPegKeys.size(); ++i) {
      if (!ImGui::IsKeyPressed(kPegKeys[i][0], false) &&
          !ImGui::IsKeyPressed(kPegKeys[i][1], false)) {
        continue;
      }
      const int label = static_cast<int>(i) + 1;
      const int pending = app.pending_from;
      app.pending_from = 0;
      if (pending == 0) {
        app.pending_from = label;
      } else if (pending != label) {
        const std::optional<std::array<int, 2>> physical =
            hanoi::labels_to_towers(app.labelling, pending, label);
        if (physical) {
          do_board_move(app, (*physical)[0], (*physical)[1]);
        }
      } else {
        // The same peg twice cancels.
      }
    }
    if (ImGui::IsKeyPressed(ImGuiKey_Escape, false)) {
      app.pending_from = 0;
    }
  }
  if (app.pending_from == 0) {
    ImGui::TextWrapped("Drag a top disc onto another peg, or type the "
                       "from-peg number, then the to-peg number (Esc "
                       "cancels).");
  } else {
    ImGui::Text("From peg %d: type the to-peg number (Esc cancels).",
                app.pending_from);
  }
}

// The always-visible Tier-1 move history: the numbered default-space (physical
// 1-2-3) move tally + live count vs the optimal 2^N-1, in a scrolling region;
// resets with a new game. Replaces the old always-on recipes panel, which moved
// to the Recipe menu (Tier 3). (feature-spec §4.11, §6.2.)
void draw_history(App &app) {
  ImGui::Separator();
  const std::vector<std::array<int, 2>> &moves = app.recorder.moves();
  ImGui::Text("History -- %zu moves (optimal %d, default 1-2-3 labels):",
              moves.size(), optimal_moves(app.game.num_disks()));
  ImGui::BeginChild("##history", ImVec2(0.0f, 96.0f), ImGuiChildFlags_Borders);
  if (moves.empty()) {
    ImGui::TextDisabled("  (no moves yet)");
  } else {
    // Clicking a move shows the board as it was after it.
    int clicked = -1;
    for (std::size_t i = 0; i < moves.size(); ++i) {
      char row[32];
      std::snprintf(row, sizeof row, "%zu. %d -> %d##hist%zu", i + 1,
                    moves[i][0], moves[i][1], i);
      if (ImGui::Selectable(row, app.review == static_cast<int>(i) + 1)) {
        clicked = static_cast<int>(i) + 1;
      }
    }
    if (clicked > 0) {
      app.review_move(clicked);
    }
  }
  ImGui::EndChild();
  if (app.review >= 0 && ImGui::Button("Back to current")) {
    app.review = -1;
    app.review_game.reset();
    app.clear_pending();
    app.status.clear();
  }
}

// A move or apply made while reviewing: continue from the reviewed move
// (deleting the later ones), or stay in review.
void draw_continue_modal(App &app) {
  if (app.open_continue) {
    ImGui::OpenPopup("Continue from here?");
    app.open_continue = false;
  }
  if (ImGui::BeginPopupModal("Continue from here?", nullptr,
                             ImGuiWindowFlags_AlwaysAutoResize)) {
    const int count = app.review;
    const int total = static_cast<int>(app.recorder.moves().size());
    if (count + 1 == total) {
      ImGui::Text("Continue from move %d? This deletes move %d.", count, total);
    } else {
      ImGui::Text("Continue from move %d? This deletes moves %d-%d.", count,
                  count + 1, total);
    }
    if (ImGui::Button("Yes")) {
      const int fp = app.pending_fp;
      const int tp = app.pending_tp;
      const std::string apply_name = app.pending_apply;
      app.clear_pending();
      app.continue_from_review();
      if (fp >= 0) {
        do_board_move(app, fp, tp);
      } else {
        apply_recipe(app, apply_name);
      }
      ImGui::CloseCurrentPopup();
    }
    ImGui::SameLine();
    if (ImGui::Button("No")) {
      app.clear_pending();
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

  // Tier-2 unlock latches at the first win (by any path -- button or applied
  // recipe) and stays for the session. First run opens "How to Play" once.
  app.won_once = app.won_once || app.won();
  if (!app.help_shown) {
    app.open_help = true;
    app.help_shown = true;
  }

  draw_menubar(app);
  draw_save_modal(app);
  draw_win_modal(app);
  draw_discard_save_modal(app);
  draw_help_modal(app);
  draw_illegal_modal(app);
  draw_continue_modal(app);

  // Tier-1 goal line + the running count vs optimal.
  ImGui::Text("Goal: move all %d discs to peg 3   (Moves: %d / optimal %d)",
              app.game.num_disks(), app.game.current_moves(),
              optimal_moves(app.game.num_disks()));
  if (app.won()) {
    ImGui::SameLine();
    ImGui::TextColored(ImVec4(0.3f, 0.9f, 0.3f, 1.0f), "  -- solved!");
  }

  draw_board(app);
  draw_moves(app);
  draw_history(app);
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
