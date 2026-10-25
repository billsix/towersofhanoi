// Copyright (c) 2026 William Emerison Six -- GNU GPL v2 or later.
//
// wxWidgets front-end for Towers of Hanoi, the C++ sibling of the Python
// wxPython GUI (hanoigui.py). It builds its window from the SHARED wx XRC
// (ui/hanoi.xrc, reached at /ui/hanoi.xrc via the Makefile mount) -- the same
// layout the Python GUI uses, so the two can't drift -- and drives the ported
// engine (src/*.hpp). Loaded at runtime (wxXmlResource::Load), so there is no
// compile-time XRC constraint. Feature parity with hanoigui.py and the
// UI-independent feature spec (tasks/reference/feature-spec.md): menubar, board
// coloured by LABEL (physical 1,2,3 reference shown when relabelled), move
// buttons in the current labels (only the legal ones enabled), the recipe list
// with Save (post-win) / Apply / Show, and the three-panel rebinding dialog on
// a relabelled apply/move. Keep the view thin -- logic lives in src/.

#include "model.hpp"
#include "presenter.hpp"
#include "recipe.hpp"

#include <wx/dcbuffer.h>
#include <wx/graphics.h>
#include <wx/numdlg.h>
#include <wx/textdlg.h>
#include <wx/wx.h>
#include <wx/xrc/xmlres.h>

#include <array>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace {

// Blue / gold / red, indexed by 0-indexed LABEL -- colour tracks the label, not
// the physical peg (matches the ImGui front-end and presenter.peg_color). Used
// for the peg label badges below the board.
const std::array<wxColour, 3> kLabelColours{
    wxColour(70, 130, 220), wxColour(220, 190, 60), wxColour(220, 80, 80)};

// Disc colour follows disc SIZE (identity), not the peg -- a disc keeps its
// colour as it moves. Ten colours (cycles past 10). Ported from
// board_renderers.py _DISC_COLOURS so the wx board matches the wxPython one.
const std::array<wxColour, 10> kDiscColours{
    wxColour(232, 80, 80),   wxColour(232, 145, 70),  wxColour(235, 200, 75),
    wxColour(170, 210, 80),  wxColour(85, 195, 130),  wxColour(75, 170, 220),
    wxColour(100, 130, 220), wxColour(160, 110, 220), wxColour(220, 110, 200),
    wxColour(185, 145, 110)};

// Board palette, ported from board_renderers.py: background gradient, peg
// cylinder gradient, base bar, the per-disc drop shadow, reference-label grey.
const wxColour kBgTop(45, 52, 68);
const wxColour kBgBottom(20, 26, 38);
const wxColour kPegLight(200, 162, 110);
const wxColour kPegDark(120, 86, 50);
const wxColour kBaseFill(150, 110, 70);
const wxColour kBaseEdge(90, 64, 38);
const wxColour kShadow(0, 0, 0, 90);
const wxColour kReferenceGrey(170, 178, 195);

// Blend c toward white / black by amount (0..1) -- the disc top/edge shading.
wxColour lighten(const wxColour &c, double a) {
  return wxColour(static_cast<unsigned char>(c.Red() + (255 - c.Red()) * a),
                  static_cast<unsigned char>(c.Green() + (255 - c.Green()) * a),
                  static_cast<unsigned char>(c.Blue() + (255 - c.Blue()) * a));
}
wxColour darken(const wxColour &c, double a) {
  return wxColour(static_cast<unsigned char>(c.Red() * (1 - a)),
                  static_cast<unsigned char>(c.Green() * (1 - a)),
                  static_cast<unsigned char>(c.Blue() * (1 - a)));
}

// Disc width: linear interpolation so the smallest disc is 1/3 the width of the
// largest -- a visible difference without being tiny
// (board_renderers._disc_width).
double disc_width(int size, int n, double max_w) {
  if (n <= 1) {
    return max_w;
  }
  const double smallest = max_w / 3.0;
  return smallest + (max_w - smallest) * (size - 1) / (n - 1);
}

// One disc: a drop shadow, then a vertical light-to-dark gradient rounded rect.
void draw_disc(wxGraphicsContext &gc, double cx, double y, double w, double h,
               const wxColour &colour) {
  gc.SetBrush(wxBrush(kShadow));
  gc.SetPen(*wxTRANSPARENT_PEN);
  wxGraphicsPath shadow = gc.CreatePath();
  shadow.AddRoundedRectangle(cx - w / 2 + 2, y + 4, w, h, h / 3);
  gc.DrawPath(shadow);
  const wxGraphicsBrush brush = gc.CreateLinearGradientBrush(
      cx, y, cx, y + h, lighten(colour, 0.30), darken(colour, 0.22));
  gc.SetBrush(brush);
  gc.SetPen(wxPen(darken(colour, 0.45), 1));
  wxGraphicsPath path = gc.CreatePath();
  path.AddRoundedRectangle(cx - w / 2, y, w, h, h / 3);
  gc.DrawPath(path);
}

// A coloured circular badge with a centred number (the peg label).
void draw_badge(wxGraphicsContext &gc, double cx, double cy, int num,
                const wxColour &colour, const wxFont &font) {
  const double r = 14;
  gc.SetBrush(wxBrush(kShadow));
  gc.SetPen(*wxTRANSPARENT_PEN);
  wxGraphicsPath shadow = gc.CreatePath();
  shadow.AddCircle(cx + 1, cy + 2, r);
  gc.DrawPath(shadow);
  gc.SetBrush(wxBrush(colour));
  gc.SetPen(wxPen(darken(colour, 0.40), 1));
  wxGraphicsPath path = gc.CreatePath();
  path.AddCircle(cx, cy, r);
  gc.DrawPath(path);
  gc.SetFont(font, *wxWHITE);
  const wxString t = wxString::Format("%d", num);
  wxDouble tw = 0;
  wxDouble th = 0;
  gc.GetTextExtent(t, &tw, &th);
  gc.DrawText(t, cx - tw / 2, cy - th / 2);
}

// (from_label, to_label) label pairs, matching hanoigui.py ALL_LABEL_PAIRS and
// the XRC move_<f>_<t> buttons.
constexpr std::array<std::array<int, 2>, 6> kLabelPairs{
    {{1, 2}, {1, 3}, {2, 1}, {2, 3}, {3, 1}, {3, 2}}};

int optimal_moves(int n) { return (1 << n) - 1; }

// Candidate paths for the shared XRC: the /ui mount (the Makefile mounts the
// repo-root ui/ there), then the in-tree symlink, then a couple of fallbacks.
wxString find_xrc() {
  const char *candidates[] = {"/ui/hanoi.xrc", "hanoi.xrc",
                              "/hanoi-cpp/hanoi.xrc", "../ui/hanoi.xrc"};
  for (const char *c : candidates) {
    if (wxFileExists(wxString::FromUTF8(c))) {
      return wxString::FromUTF8(c);
    }
  }
  return wxString::FromUTF8("/ui/hanoi.xrc");
}

// The board: a custom-drawn wxPanel (graphics by default; a text listing under
// View -> Board Style -> Text). Colour follows the label; the physical 1,2,3
// reference is shown under the labels when relabelled.
class BoardView {
public:
  void attach(wxWindow *slot) { slot_ = slot; }
  void set_state(const hanoi::Game *game, hanoi::Labelling labelling) {
    game_ = game;
    labelling_ = labelling;
    if (slot_ != nullptr) {
      slot_->Refresh();
    }
  }
  void set_graphics(bool graphics) {
    graphics_ = graphics;
    if (slot_ != nullptr) {
      slot_->Refresh();
    }
  }

  bool has_game() const { return game_ != nullptr && game_->num_disks() > 0; }
  bool use_graphics() const { return graphics_; }

  // Graphics board, ported faithfully from the Python GraphicsBoardRenderer
  // (board_renderers.py): a background gradient, a base bar, cylinder pegs,
  // size-coloured gradient rounded discs with a drop shadow, and label badges
  // (+ the physical 1,2,3 reference row when relabelled). Uses
  // wxGraphicsContext for antialiasing + gradients -- C++ wxWidgets has it
  // (unlike Rust's wxDragon, which was limited to wxDC and drew flat
  // rectangles).
  void paint_graphics(wxGraphicsContext &gc, const wxSize &sz) const {
    const int n = game_->num_disks();
    const double w = sz.GetWidth();
    const double h = sz.GetHeight();

    gc.SetPen(*wxTRANSPARENT_PEN);
    const wxGraphicsBrush bg =
        gc.CreateLinearGradientBrush(0, 0, 0, h, kBgTop, kBgBottom);
    gc.SetBrush(bg);
    wxGraphicsPath bgp = gc.CreatePath();
    bgp.AddRectangle(0, 0, w, h);
    gc.DrawPath(bgp);

    const bool relabelled = labelling_ != hanoi::Labelling::OneTwoThree;
    const double margin = 20.0;
    const double label_band = relabelled ? 60.0 : 36.0;
    const double base_h = 14.0;
    const double avail_w = std::max(80.0, w - 2 * margin);
    const double avail_h = std::max(80.0, h - 2 * margin - label_band - base_h);
    const double peg_zone_w = avail_w / 3.0;
    const double disc_h = std::min(avail_h / std::max(n, 4) * 0.92, 30.0);
    const double max_disc_w = peg_zone_w * 0.92;
    const double peg_w = std::max(8.0, max_disc_w * 0.07);
    const double peg_h = avail_h * 0.95;
    const double base_y = h - margin - label_band - base_h;
    const double peg_top_y = base_y - peg_h;
    std::array<double, 3> peg_cx{};
    for (int i = 0; i < 3; ++i) {
      peg_cx[static_cast<std::size_t>(i)] = margin + peg_zone_w * (i + 0.5);
    }

    gc.SetBrush(wxBrush(kBaseFill));
    gc.SetPen(wxPen(kBaseEdge, 1));
    wxGraphicsPath basep = gc.CreatePath();
    basep.AddRoundedRectangle(margin, base_y, w - 2 * margin, base_h, 4);
    gc.DrawPath(basep);

    for (const double cx : peg_cx) {
      const wxGraphicsBrush pegb = gc.CreateLinearGradientBrush(
          cx - peg_w / 2, 0, cx + peg_w / 2, 0, kPegDark, kPegLight);
      gc.SetBrush(pegb);
      gc.SetPen(wxPen(kPegDark, 1));
      wxGraphicsPath pegp = gc.CreatePath();
      pegp.AddRoundedRectangle(cx - peg_w / 2, peg_top_y, peg_w, peg_h,
                               peg_w / 2);
      gc.DrawPath(pegp);
    }

    // Discs bottom-up; colour by SIZE so a disc keeps its colour as it moves.
    for (int peg = 0; peg < 3; ++peg) {
      const double cx = peg_cx[static_cast<std::size_t>(peg)];
      const std::vector<int> &stack =
          game_->towers()[static_cast<std::size_t>(peg)];
      for (std::size_t level = 0; level < stack.size(); ++level) {
        const int size = stack[level];
        const double dw = disc_width(size, n, max_disc_w);
        const double y =
            base_y - (static_cast<double>(level) + 1) * disc_h * 1.04;
        draw_disc(gc, cx, y, dw, disc_h,
                  kDiscColours[static_cast<std::size_t>((size - 1) % 10)]);
      }
    }

    const double active_label_y =
        base_y + base_h + (relabelled ? 18.0 : label_band / 2.0);
    const wxFont badge_font(wxFontInfo(12).Bold());
    for (int peg = 0; peg < 3; ++peg) {
      const double cx = peg_cx[static_cast<std::size_t>(peg)];
      const int label = hanoi::change_labels_on_pegs(labelling_, peg);
      draw_badge(gc, cx, active_label_y, label + 1,
                 kLabelColours[static_cast<std::size_t>(label)], badge_font);
    }
    if (relabelled) {
      const double ref_y = active_label_y + 26.0;
      gc.SetFont(wxFont(wxFontInfo(10)), kReferenceGrey);
      for (int peg = 0; peg < 3; ++peg) {
        const double cx = peg_cx[static_cast<std::size_t>(peg)];
        const wxString t = wxString::Format("%d", peg + 1);
        wxDouble tw = 0;
        wxDouble th = 0;
        gc.GetTextExtent(t, &tw, &th);
        gc.DrawText(t, cx - tw / 2, ref_y - th / 2);
      }
    }
  }

  void paint_text(wxDC &dc) const {
    dc.SetFont(wxFont(wxFontInfo(11).Family(wxFONTFAMILY_TELETYPE)));
    dc.SetTextForeground(*wxBLACK);
    int y = 8;
    for (int peg = 0; peg < 3; ++peg) {
      const int label = hanoi::change_labels_on_pegs(labelling_, peg) + 1;
      wxString line = wxString::Format("peg %d (label %d): ", peg + 1, label);
      for (const int size : game_->towers()[static_cast<std::size_t>(peg)]) {
        line += wxString::Format("%d ", size);
      }
      dc.DrawText(line, 8, y);
      y += 24;
    }
  }

private:
  wxWindow *slot_ = nullptr;
  const hanoi::Game *game_ = nullptr;
  hanoi::Labelling labelling_ = hanoi::Labelling::OneTwoThree;
  bool graphics_ = true;
};

class HanoiFrame : public wxFrame {
public:
  HanoiFrame()
      : wxFrame(nullptr, wxID_ANY, "Towers of Hanoi", wxDefaultPosition,
                wxSize(1100, 650)) {
    build_menu_bar();
    CreateStatusBar(2);
    const int status_widths[] = {-1, 140};
    SetStatusWidths(2, status_widths);
    build_ui();
    new_game(kDefaultDisks);
    Centre();
  }

private:
  static constexpr int kDefaultDisks = 3;
  static constexpr int kMaxDisks = 10;

  wxXmlResource *xrc() { return wxXmlResource::Get(); }

  void build_menu_bar() {
    wxMenuBar *mb = xrc()->LoadMenuBar("main_menubar");
    SetMenuBar(mb);
    Bind(wxEVT_MENU, &HanoiFrame::on_new_game_prompt, this, XRCID("wxID_NEW"));
    Bind(wxEVT_MENU, &HanoiFrame::on_new_game_same, this,
         XRCID("game_new_same"));
    Bind(wxEVT_MENU, [this](wxCommandEvent &) { Close(); }, XRCID("wxID_EXIT"));
    Bind(wxEVT_MENU, &HanoiFrame::on_about, this, XRCID("wxID_ABOUT"));
    Bind(
        wxEVT_MENU, [this](wxCommandEvent &) { set_graphics(false); },
        XRCID("style_text"));
    Bind(
        wxEVT_MENU, [this](wxCommandEvent &) { set_graphics(true); },
        XRCID("style_graphics"));
    for (const std::array<int, 3> &labels : kRelabelPerms) {
      const wxString id =
          wxString::Format("relabel_%d_%d_%d", labels[0], labels[1], labels[2]);
      const int item_id = wxXmlResource::GetXRCID(id);
      wxMenuItem *item = mb->FindItem(item_id);
      relabel_items_.push_back({labels, item, item->GetItemLabel()});
      Bind(
          wxEVT_MENU, [this, labels](wxCommandEvent &) { on_relabel(labels); },
          item_id);
    }
  }

  void build_ui() {
    wxPanel *panel = xrc()->LoadPanel(this, "HanoiPanel");
    wxBoxSizer *sizer = new wxBoxSizer(wxVERTICAL);
    sizer->Add(panel, 1, wxEXPAND);
    SetSizer(sizer);

    board_slot_ = XRCCTRL(*this, "board_slot", wxPanel);
    recipe_list_ = XRCCTRL(*this, "recipe_list", wxListBox);
    save_btn_ = XRCCTRL(*this, "recipe_save", wxButton);
    apply_btn_ = XRCCTRL(*this, "recipe_apply", wxButton);
    show_btn_ = XRCCTRL(*this, "recipe_show", wxButton);

    board_.attach(board_slot_);
    board_slot_->SetBackgroundStyle(wxBG_STYLE_PAINT);
    board_slot_->Bind(wxEVT_PAINT, [this](wxPaintEvent &) {
      wxPaintDC dc(board_slot_);
      if (!board_.has_game()) {
        dc.SetBackground(*wxWHITE_BRUSH);
        dc.Clear();
        return;
      }
      if (board_.use_graphics()) {
        // GTK double-buffers natively, so a wxPaintDC (a wxWindowDC, which
        // wxGraphicsContext::Create accepts) is flicker-free here.
        const std::unique_ptr<wxGraphicsContext> gc(
            wxGraphicsContext::Create(dc));
        if (gc) {
          board_.paint_graphics(*gc, board_slot_->GetClientSize());
        }
      } else {
        dc.SetBackground(*wxWHITE_BRUSH);
        dc.Clear();
        board_.paint_text(dc);
      }
    });

    for (const std::array<int, 2> &p : kLabelPairs) {
      // Dynamic XRC id -> use GetXRCID + FindWindow (XRCCTRL/XRCID wrap their
      // argument in wxT(), so they only take string literals, not variables).
      const int xid =
          wxXmlResource::GetXRCID(wxString::Format("move_%d_%d", p[0], p[1]));
      move_buttons_[static_cast<std::size_t>(label_pair_index(p[0], p[1]))] =
          wxDynamicCast(FindWindow(xid), wxButton);
      const int fl = p[0];
      const int tl = p[1];
      Bind(
          wxEVT_BUTTON, [this, fl, tl](wxCommandEvent &) { on_move(fl, tl); },
          xid);
    }

    Bind(wxEVT_BUTTON, &HanoiFrame::on_save, this, XRCID("recipe_save"));
    Bind(wxEVT_BUTTON, &HanoiFrame::on_apply, this, XRCID("recipe_apply"));
    Bind(wxEVT_BUTTON, &HanoiFrame::on_show, this, XRCID("recipe_show"));
    recipe_list_->Bind(wxEVT_LISTBOX_DCLICK,
                       [this](wxCommandEvent &) { on_show_selected(); });
  }

  // --- Engine helpers --------------------------------------------------

  static int label_pair_index(int fl, int tl) {
    for (std::size_t i = 0; i < kLabelPairs.size(); ++i) {
      if (kLabelPairs[i][0] == fl && kLabelPairs[i][1] == tl) {
        return static_cast<int>(i);
      }
    }
    return 0;
  }

  void new_game(int n) {
    disk_count_ = n;
    game_ = hanoi::Game(n);
    recorder_.reset();
    labelling_ = hanoi::Labelling::OneTwoThree;
    refresh();
  }

  bool won() const { return game_.check_win_condition(); }

  void do_move(int fp, int tp) {
    game_.apply(hanoi::Move{fp, tp});
    recorder_.record(fp + 1, tp + 1);
  }

  // --- Event handlers --------------------------------------------------

  void on_new_game_prompt(wxCommandEvent &) {
    const long n = wxGetNumberFromUser("How many discs?", "Discs:", "New Game",
                                       disk_count_, 1, kMaxDisks, this);
    if (n < 1) {
      return; // cancelled
    }
    new_game(static_cast<int>(n));
    set_status("");
  }

  void on_new_game_same(wxCommandEvent &) {
    new_game(disk_count_);
    set_status("");
  }

  void on_about(wxCommandEvent &) {
    wxMessageBox("Towers of Hanoi\n\n"
                 "A teaching tool for solving Hanoi by hand: solve small, "
                 "relabel pegs, replay.\n\n"
                 "Shares the engine (src/) with the ImGui and Python "
                 "front-ends; built from the shared wx XRC.",
                 "About Towers of Hanoi", wxOK | wxICON_INFORMATION, this);
  }

  void on_move(int from_label, int to_label) {
    const bool relabelled = labelling_ != hanoi::Labelling::OneTwoThree;
    const std::optional<std::array<int, 2>> physical =
        hanoi::labels_to_towers(labelling_, from_label, to_label);
    if (!physical) {
      return;
    }
    // Buttons are enabled only when legal, so this move is legal.
    do_move((*physical)[0], (*physical)[1]);
    set_status(wxString::Format("Moved %d -> %d.", from_label, to_label));
    if (relabelled) {
      show_rebinding("Rebinding for your move",
                     "You typed this move in the current (relabelled) labels. "
                     "Here is how each label maps to a physical peg now, and "
                     "where your move went.",
                     "Your move", {{{from_label, to_label}}});
    }
    refresh();
    if (won()) {
      on_win();
    }
  }

  void on_relabel(const std::array<int, 3> &labels) {
    for (const hanoi::Labelling l : hanoi::kAllLabellings) {
      const std::array<int, 3> order = hanoi::label_order(l);
      if (order[0] + 1 == labels[0] && order[1] + 1 == labels[1] &&
          order[2] + 1 == labels[2]) {
        labelling_ = l;
        break;
      }
    }
    set_status(wxString::Format("Relabelled: physical pegs 1,2,3 now show as "
                                "%d,%d,%d.",
                                labels[0], labels[1], labels[2]));
    refresh();
  }

  void on_apply(wxCommandEvent &) {
    const std::optional<std::string> name = selected_recipe();
    if (!name) {
      set_status("Select a recipe first.");
      return;
    }
    const hanoi::Recipe *r = registry_.get(*name);
    if (r == nullptr) {
      return;
    }
    const bool relabelled = labelling_ != hanoi::Labelling::OneTwoThree;
    const std::vector<hanoi::StepResult> res =
        hanoi::apply(*r, game_, labelling_);
    int applied = 0;
    std::string err;
    for (const hanoi::StepResult &s : res) {
      if (s.ok()) {
        ++applied;
        recorder_.record(*s.from_peg + 1, *s.to_peg + 1);
      } else {
        err = *s.error;
      }
    }
    set_status(wxString::Format("Applied '%s' - %d/%zu moves%s", name->c_str(),
                                applied, r->default_moves.size(),
                                err.empty() ? "." : (" - stopped: " + err)));
    if (relabelled) {
      show_rebinding(
          wxString::Format("Rebinding for '%s'", name->c_str()),
          "This recipe is written in labels 1, 2, 3. Because you relabelled, "
          "each move is rebound to a physical peg -- the same solution, new "
          "labels.",
          "Recipe moves", r->default_moves);
    }
    refresh();
    if (won()) {
      on_win();
    }
  }

  void on_show(wxCommandEvent &) { on_show_selected(); }

  void on_show_selected() {
    const std::optional<std::string> name = selected_recipe();
    if (!name) {
      set_status("Select a recipe first.");
      return;
    }
    const hanoi::Recipe *r = registry_.get(*name);
    if (r == nullptr) {
      return;
    }
    wxDialog *dlg = xrc()->LoadDialog(this, "RecipeDialog");
    dlg->SetTitle(wxString::Format("Recipe '%s'", name->c_str()));
    wxListBox *steps = XRCCTRL(*dlg, "recipe_steps", wxListBox);
    steps->SetFont(wxFont(wxFontInfo(12).Family(wxFONTFAMILY_TELETYPE)));
    const std::size_t n = r->default_moves.size();
    steps->Append(wxString::Format(
        "Recipe '%s' (%d discs, %zu moves):", name->c_str(), r->disk_count, n));
    for (std::size_t i = 0; i < n; ++i) {
      steps->Append(wxString::Format("  step %zu: %d -> %d", i + 1,
                                     r->default_moves[i][0],
                                     r->default_moves[i][1]));
    }
    dlg->Bind(
        wxEVT_BUTTON, [dlg](wxCommandEvent &) { dlg->Destroy(); }, wxID_CLOSE);
    dlg->Bind(wxEVT_CLOSE_WINDOW, [dlg](wxCloseEvent &) { dlg->Destroy(); });
    dlg->Fit();
    dlg->Show();
  }

  void on_save(wxCommandEvent &) {
    // Enabled only when won.
    wxTextEntryDialog dlg(this, "Recipe name:", "Save Recipe",
                          wxString::Format("solve-%d", game_.num_disks()));
    if (dlg.ShowModal() != wxID_OK) {
      return;
    }
    const wxString name = dlg.GetValue().Trim().Trim(false);
    if (name.IsEmpty()) {
      return;
    }
    const std::string key = name.ToStdString();
    const bool overwrote = registry_.get(key) != nullptr;
    registry_.save(recorder_.to_recipe(key, game_.num_disks()));
    set_status((overwrote ? "Overwrote recipe '" : "Saved recipe '") + name +
               "'.");
    refresh_recipes(key);
  }

  void on_win() {
    const int mm = optimal_moves(game_.num_disks());
    const int mv = game_.current_moves();
    const wxString verdict =
        mv == mm
            ? "Optimal!"
            : wxString::Format("%d more than the minimum (%d).", mv - mm, mm);
    set_status(wxString::Format("Solved in %d moves - %s  Click 'Save Current "
                                "Solution' to keep it as a recipe.",
                                mv, verdict));
  }

  // --- Three-panel rebinding dialog (RebindingDialog in the XRC) -------

  void show_rebinding(const wxString &title, const wxString &intro,
                      const wxString &left_header,
                      const std::vector<std::array<int, 2>> &moves) {
    if (rebinding_dlg_ != nullptr) {
      rebinding_dlg_->Destroy();
      rebinding_dlg_ = nullptr;
    }
    wxDialog *dlg = xrc()->LoadDialog(this, "RebindingDialog");
    dlg->SetTitle(title);
    const wxFont mono(wxFontInfo(12).Family(wxFONTFAMILY_TELETYPE));
    XRCCTRL(*dlg, "rebind_intro", wxStaticText)->SetLabel(intro);
    XRCCTRL(*dlg, "rebind_left_header", wxStaticText)->SetLabel(left_header);

    const std::array<std::array<int, 2>, 3> key = hanoi::rebinding(labelling_);
    wxString key_text;
    for (std::size_t i = 0; i < key.size(); ++i) {
      key_text += wxString::Format("label %d -> peg %d", key[i][0], key[i][1]);
      if (i + 1 < key.size()) {
        key_text += "\n";
      }
    }
    wxStaticText *key_ctrl = XRCCTRL(*dlg, "rebind_key", wxStaticText);
    key_ctrl->SetLabel(key_text);
    key_ctrl->SetFont(mono);

    const std::vector<std::array<int, 2>> rebound =
        hanoi::rebound_moves(moves, labelling_);
    wxListBox *left = XRCCTRL(*dlg, "rebind_left", wxListBox);
    wxListBox *right = XRCCTRL(*dlg, "rebind_right", wxListBox);
    left->SetFont(mono);
    right->SetFont(mono);
    for (std::size_t i = 0; i < moves.size(); ++i) {
      left->Append(
          wxString::Format("%zu: %d -> %d", i + 1, moves[i][0], moves[i][1]));
      right->Append(wxString::Format("%zu: %d -> %d", i + 1, rebound[i][0],
                                     rebound[i][1]));
    }

    dlg->Bind(
        wxEVT_BUTTON,
        [this, dlg](wxCommandEvent &) {
          rebinding_dlg_ = nullptr;
          dlg->Destroy();
        },
        wxID_CLOSE);
    dlg->Bind(wxEVT_CLOSE_WINDOW, [this, dlg](wxCloseEvent &) {
      rebinding_dlg_ = nullptr;
      dlg->Destroy();
    });
    dlg->Fit();
    dlg->Show();
    rebinding_dlg_ = dlg;
  }

  // --- State sync ------------------------------------------------------

  std::optional<std::string> selected_recipe() {
    const int idx = recipe_list_->GetSelection();
    if (idx == wxNOT_FOUND) {
      return std::nullopt;
    }
    const auto it = list_index_to_name_.find(idx);
    if (it == list_index_to_name_.end()) {
      return std::nullopt;
    }
    return it->second;
  }

  void set_graphics(bool graphics) {
    board_.set_graphics(graphics);
    board_.set_state(&game_, labelling_);
  }

  void refresh() {
    board_.set_state(&game_, labelling_);
    const bool w = won();
    SetStatusText(wxString::Format("Moves: %d", game_.current_moves()), 1);

    std::array<bool, 6> legal{};
    for (const hanoi::Move &m : game_.move_options()) {
      const int fl = hanoi::change_labels_on_pegs(labelling_, m.from_peg) + 1;
      const int tl = hanoi::change_labels_on_pegs(labelling_, m.to_peg) + 1;
      legal[static_cast<std::size_t>(label_pair_index(fl, tl))] = true;
    }
    for (std::size_t i = 0; i < move_buttons_.size(); ++i) {
      if (move_buttons_[i] != nullptr) {
        move_buttons_[i]->Enable(!w && legal[i]);
      }
    }

    const std::array<int, 3> cur{
        hanoi::change_labels_on_pegs(labelling_, 0) + 1,
        hanoi::change_labels_on_pegs(labelling_, 1) + 1,
        hanoi::change_labels_on_pegs(labelling_, 2) + 1};
    for (const RelabelItem &ri : relabel_items_) {
      const bool active = ri.labels[0] == cur[0] && ri.labels[1] == cur[1] &&
                          ri.labels[2] == cur[2];
      ri.item->SetItemLabel(
          (active ? wxString::FromUTF8("\xe2\x97\x8f  ") : wxString("     ")) +
          ri.base_label);
      ri.item->Enable(!w);
    }
    apply_btn_->Enable(!w);
    show_btn_->Enable(true);
    save_btn_->Enable(w);
    refresh_recipes(std::string());
  }

  void refresh_recipes(const std::string &select) {
    const std::optional<std::string> previous = selected_recipe();
    recipe_list_->Clear();
    list_index_to_name_.clear();
    const std::vector<std::string> names = registry_.names();
    for (std::size_t i = 0; i < names.size(); ++i) {
      const hanoi::Recipe *r = registry_.get(names[i]);
      recipe_list_->Append(
          wxString::Format("%s  (%d discs, %zu moves)", names[i].c_str(),
                           r != nullptr ? r->disk_count : 0,
                           r != nullptr ? r->default_moves.size() : 0));
      list_index_to_name_[static_cast<int>(i)] = names[i];
    }
    const std::string chosen =
        !select.empty() ? select : (previous ? *previous : std::string());
    for (std::size_t i = 0; i < names.size(); ++i) {
      if (names[i] == chosen) {
        recipe_list_->SetSelection(static_cast<int>(i));
        break;
      }
    }
  }

  void set_status(const wxString &text) { SetStatusText(text, 0); }

  // --- Data ------------------------------------------------------------

  struct RelabelItem {
    std::array<int, 3> labels;
    wxMenuItem *item;
    wxString base_label;
  };

  static const std::array<std::array<int, 3>, 6> kRelabelPerms;

  hanoi::Game game_{kDefaultDisks};
  hanoi::Labelling labelling_ = hanoi::Labelling::OneTwoThree;
  hanoi::Recorder recorder_;
  hanoi::RecipeRegistry registry_;
  int disk_count_ = kDefaultDisks;

  BoardView board_;
  wxPanel *board_slot_ = nullptr;
  wxListBox *recipe_list_ = nullptr;
  wxButton *save_btn_ = nullptr;
  wxButton *apply_btn_ = nullptr;
  wxButton *show_btn_ = nullptr;
  std::array<wxButton *, 6> move_buttons_{};
  std::vector<RelabelItem> relabel_items_;
  std::map<int, std::string> list_index_to_name_;
  wxDialog *rebinding_dlg_ = nullptr;
};

const std::array<std::array<int, 3>, 6> HanoiFrame::kRelabelPerms{
    {{1, 2, 3}, {1, 3, 2}, {2, 1, 3}, {2, 3, 1}, {3, 1, 2}, {3, 2, 1}}};

class HanoiApp : public wxApp {
public:
  bool OnInit() override {
    wxImage::AddHandler(new wxPNGHandler());
    wxXmlResource::Get()->InitAllHandlers();
    if (!wxXmlResource::Get()->Load(find_xrc())) {
      wxLogError("Could not load the shared hanoi.xrc (looked at /ui/hanoi.xrc "
                 "and ./hanoi.xrc). The Makefile mounts the repo-root ui/ at "
                 "/ui; run via `make wx`.");
      return false;
    }
    (new HanoiFrame())->Show(true);
    return true;
  }
};

} // namespace

wxIMPLEMENT_APP(HanoiApp);
