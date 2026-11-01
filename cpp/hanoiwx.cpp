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

#include <wx/config.h>
#include <wx/dcbuffer.h>
#include <wx/graphics.h>
#include <wx/numdlg.h>
#include <wx/textdlg.h>
#include <wx/wx.h>
#include <wx/xrc/xmlres.h>

#include <array>
#include <cmath>
#include <functional>
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

// Tier-1 onboarding text (How to Play), mirroring hanoigui.py HOWTO_TEXT. The
// goal itself lives in the status bar; this teaches the one rule and the
// method the game exists to show (solve small, relabel, replay).
const char *kHowtoText =
    "Move the whole stack of discs from peg 1 to peg 3.\n"
    "- Move one disc at a time -- always the top disc of a peg.\n"
    "- Never place a larger disc on a smaller one.\n"
    "\n"
    "The method this teaches: solve a SMALL stack, then RELABEL the pegs to\n"
    "reuse that solution for a bigger stack -- \"solve small, relabel, "
    "replay.\"\n"
    "Relabelling and saved recipes unlock after your first win.";

// wx.Config key: show the How-to-Play panel on launch. Cleared by the panel's
// "Don't show this again" checkbox; re-shown any time from Help / View.
const char *kConfigShowHowto = "show_howto_on_start";

// Legal-move diagram palette (hanoigui.py _LegalMoveDiagram): the two example
// discs, and the green/red accents for the allowed/forbidden captions.
const wxColour kDiagDiscFill(210, 210, 215);
const wxColour kDiagDiscEdge(30, 30, 40);
const wxColour kDiagOk(40, 150, 60);
const wxColour kDiagNo(200, 55, 55);

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
  void paint_graphics(wxGraphicsContext &gc, const wxSize &sz) {
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
    geo_cx_ = peg_cx; // cache for mouse hit-testing (drag-drop)

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
        // Omit the disc currently being dragged from its home peg.
        if (drag_src_ == peg && level == stack.size() - 1) {
          continue;
        }
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

    // The dragged disc follows the cursor, drawn on top in its size colour.
    if (drag_src_ >= 0) {
      const double dw = disc_width(drag_size_, n, max_disc_w);
      draw_disc(gc, drag_x_, drag_y_ - disc_h / 2.0, dw, disc_h,
                kDiscColours[static_cast<std::size_t>((drag_size_ - 1) % 10)]);
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

  // --- Drag-and-drop (spike, mirrors the wxPython GraphicsBoardRenderer) ---

  void set_move_callback(std::function<void(int, int)> cb) {
    move_cb_ = std::move(cb);
  }
  // Enable/disable disc dragging (off once the game is won).
  void set_interactive(bool interactive) {
    interactive_ = interactive;
    if (!interactive) {
      end_drag();
    }
  }
  void on_left_down(wxMouseEvent &evt) {
    if (!interactive_ || game_ == nullptr) {
      evt.Skip();
      return;
    }
    const int peg = peg_at(evt.GetX());
    const std::vector<int> &stack =
        game_->towers()[static_cast<std::size_t>(peg)];
    if (stack.empty()) {
      evt.Skip();
      return;
    }
    drag_src_ = peg;
    drag_size_ = stack.back();
    drag_x_ = evt.GetX();
    drag_y_ = evt.GetY();
    if (slot_ != nullptr && !slot_->HasCapture()) {
      slot_->CaptureMouse();
    }
    refresh_slot();
  }
  void on_motion(wxMouseEvent &evt) {
    if (drag_src_ < 0) {
      evt.Skip();
      return;
    }
    drag_x_ = evt.GetX();
    drag_y_ = evt.GetY();
    refresh_slot();
  }
  void on_left_up(wxMouseEvent &evt) {
    if (drag_src_ < 0) {
      evt.Skip();
      return;
    }
    const int src = drag_src_;
    const int target = peg_at(evt.GetX());
    end_drag();
    refresh_slot(); // snap back to the true board state
    if (target != src && move_cb_) {
      move_cb_(src, target);
    }
  }
  void on_capture_lost(wxMouseCaptureLostEvent &) {
    drag_src_ = -1;
    refresh_slot();
  }

private:
  void refresh_slot() {
    if (slot_ != nullptr) {
      slot_->Refresh();
    }
  }
  // The physical peg (0,1,2) whose centre is nearest x -- forgiving targeting.
  int peg_at(double x) const {
    int best = 0;
    for (int i = 1; i < 3; ++i) {
      if (std::fabs(x - geo_cx_[static_cast<std::size_t>(i)]) <
          std::fabs(x - geo_cx_[static_cast<std::size_t>(best)])) {
        best = i;
      }
    }
    return best;
  }
  void end_drag() {
    drag_src_ = -1;
    if (slot_ != nullptr && slot_->HasCapture()) {
      slot_->ReleaseMouse();
    }
  }

  wxWindow *slot_ = nullptr;
  const hanoi::Game *game_ = nullptr;
  hanoi::Labelling labelling_ = hanoi::Labelling::OneTwoThree;
  bool graphics_ = true;
  // Peg centres captured each paint, for mouse hit-testing; the in-progress
  // drag (physical src peg, its disc size, cursor position); the interactive
  // flag; and the drop callback (physical from/to pegs -> the frame).
  std::array<double, 3> geo_cx_{};
  int drag_src_ = -1;
  int drag_size_ = 0;
  double drag_x_ = 0.0;
  double drag_y_ = 0.0;
  bool interactive_ = true;
  std::function<void(int, int)> move_cb_;
};

// A small figure teaching the one rule: a smaller disc may rest on a larger
// one (left, allowed); a larger disc may never rest on a smaller one (right,
// forbidden). It illustrates the RULE, not a screenshot -- the live board is
// the app's own best picture. Ported from hanoigui.py _LegalMoveDiagram.
class LegalMoveDiagram : public wxPanel {
public:
  explicit LegalMoveDiagram(wxWindow *parent)
      : wxPanel(parent, wxID_ANY, wxDefaultPosition, wxSize(300, 108)) {
    SetMinSize(wxSize(300, 108));
    SetBackgroundStyle(wxBG_STYLE_PAINT);
    Bind(wxEVT_PAINT, &LegalMoveDiagram::on_paint, this);
  }

private:
  void on_paint(wxPaintEvent &) {
    wxPaintDC dc(this);
    dc.SetBackground(wxBrush(GetBackgroundColour()));
    dc.Clear();
    const std::unique_ptr<wxGraphicsContext> gc(wxGraphicsContext::Create(dc));
    if (!gc) {
      return;
    }
    const double width = GetClientSize().GetWidth();
    const double half = width / 2.0;
    draw_example(*gc, 0.0, half, true);
    draw_example(*gc, half, half, false);
  }

  // One two-disc stack centred in [x0, x0+width]: wide-under-narrow when legal,
  // else narrow-under-wide struck through, with a caption.
  void draw_example(wxGraphicsContext &gc, double x0, double width,
                    bool legal) {
    const double cx = x0 + width / 2.0;
    const double disc_h = 16.0;
    const double top_y = 42.0;
    const double big_w = 78.0;
    const double small_w = 42.0;
    const double bottom_w = legal ? big_w : small_w;
    const double upper_w = legal ? small_w : big_w;
    const wxColour accent = legal ? kDiagOk : kDiagNo;

    gc.SetPen(wxPen(kDiagDiscEdge, 1));
    gc.SetBrush(wxBrush(kDiagDiscFill));
    const std::array<std::array<double, 2>, 2> discs{
        {{bottom_w, top_y + disc_h}, {upper_w, top_y}}};
    for (const std::array<double, 2> &d : discs) {
      wxGraphicsPath path = gc.CreatePath();
      path.AddRoundedRectangle(cx - d[0] / 2.0, d[1], d[0], disc_h, 4.0);
      gc.DrawPath(path);
    }

    if (!legal) {
      gc.SetPen(wxPen(accent, 3));
      gc.StrokeLine(cx - big_w / 2.0, top_y - 4.0, cx + big_w / 2.0,
                    top_y + disc_h + 4.0);
    }

    const wxString caption =
        legal ? wxString::FromUTF8("\xe2\x9c\x93  smaller on larger")
              : wxString::FromUTF8("\xe2\x9c\x97  larger on smaller");
    gc.SetFont(GetFont(), accent);
    wxDouble tw = 0;
    wxDouble th = 0;
    wxDouble td = 0;
    wxDouble te = 0;
    gc.GetTextExtent(caption, &tw, &th, &td, &te);
    gc.DrawText(caption, cx - tw / 2.0, 84.0);
  }
};

class HanoiFrame : public wxFrame {
public:
  HanoiFrame()
      : wxFrame(nullptr, wxID_ANY, "Towers of Hanoi", wxDefaultPosition,
                wxSize(1100, 650)) {
    config_ = wxConfigBase::Get();
    build_menu_bar();
    CreateStatusBar(3);
    // Field 0 = the persistent goal line; field 1 stretches for action
    // feedback; field 2 is fixed-width for the moves counter at the right.
    const int status_widths[] = {-1, -2, 140};
    SetStatusWidths(3, status_widths);
    build_ui();
    new_game(kDefaultDisks);
    Centre();
    // Show the first-run How-to-Play dialog after the frame is up and the event
    // loop is running (CallAfter defers past Show()), so the modal is centered
    // over a painted window.
    CallAfter([this]() { maybe_show_howto(); });
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

    // Recipe menu (Tier 3, feature-spec §3.5) -- recipes live here, not in the
    // workspace. "Save Current Solution" (Ctrl+S) is the fixed head; below a
    // separator, rebuild_recipe_menu lists each saved recipe as a submenu
    // expanding to View / Apply, so the user points at the recipe itself.
    // Built programmatically so the shared ui/hanoi.xrc stays untouched, as
    // the wxPython oracle does.
    recipe_menu_ = new wxMenu();
    recipe_save_item_ =
        recipe_menu_->Append(wxID_ANY, "&Save Current Solution\tCtrl+S",
                             "Save the just-won solution as a reusable recipe");
    recipe_menu_->AppendSeparator();
    relabel_menu_pos_ = mb->FindMenu("Relabel pegs");
    recipe_menu_pos_ = relabel_menu_pos_ + 1;
    mb->Insert(static_cast<std::size_t>(recipe_menu_pos_), recipe_menu_,
               "&Recipe");
    Bind(wxEVT_MENU, &HanoiFrame::on_save, this, recipe_save_item_->GetId());
    rebuild_recipe_menu();

    // View menu: the always-visible move-history toggle, appended to the
    // existing (XRC) View menu. (How-to-Play is a dialog now, not a toggled
    // panel, so it lives only on the Help menu below.)
    const int view_pos = mb->FindMenu("View");
    wxMenu *view_menu = mb->GetMenu(static_cast<std::size_t>(view_pos));
    view_menu->AppendSeparator();
    history_toggle_ = view_menu->AppendCheckItem(
        wxID_ANY, "Move &history\tCtrl+H",
        "Show the running list of moves in default 1-2-3 labels");
    history_toggle_->Check(true);
    Bind(wxEVT_MENU, &HanoiFrame::on_toggle_history, this,
         history_toggle_->GetId());

    // Help -> How to Play: reopen the Tier-1 onboarding at any time
    // (recognition over recall). Added programmatically so the shared XRC Help
    // menu is untouched here.
    const int help_pos = mb->FindMenu("Help");
    if (help_pos >= 0) {
      wxMenu *help_menu = mb->GetMenu(static_cast<std::size_t>(help_pos));
      wxMenuItem *help_howto_item = help_menu->Insert(
          0, wxID_ANY, "How to &Play", "Show the goal and the rules");
      help_menu->InsertSeparator(1);
      Bind(wxEVT_MENU, &HanoiFrame::on_help_howto, this,
           help_howto_item->GetId());
    }
  }

  void build_ui() {
    panel_ = xrc()->LoadPanel(this, "HanoiPanel");

    board_slot_ = XRCCTRL(*this, "board_slot", wxPanel);
    recipe_list_ = XRCCTRL(*this, "recipe_list", wxListBox);

    // Tier 3: hide the in-panel recipe sidebar -- recipes move to the Recipe
    // menu (feature-spec §3.5). The shared XRC still defines these controls
    // for the other wx front-ends, so we only hide them here.
    hide_recipe_sidebar();

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

    // Disc drag-drop (spike): forward the board panel's mouse events to the
    // BoardView, and point its drop callback at on_board_drop (physical pegs ->
    // current labels -> the shared on_move). The move buttons stay as the
    // keyboard/accessible path. Mirrors the wxPython oracle.
    board_slot_->Bind(wxEVT_LEFT_DOWN,
                      [this](wxMouseEvent &e) { board_.on_left_down(e); });
    board_slot_->Bind(wxEVT_MOTION,
                      [this](wxMouseEvent &e) { board_.on_motion(e); });
    board_slot_->Bind(wxEVT_LEFT_UP,
                      [this](wxMouseEvent &e) { board_.on_left_up(e); });
    board_slot_->Bind(
        wxEVT_MOUSE_CAPTURE_LOST,
        [this](wxMouseCaptureLostEvent &e) { board_.on_capture_lost(e); });
    board_.set_move_callback(
        [this](int from_peg, int to_peg) { on_board_drop(from_peg, to_peg); });

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

    // Frame layout: [board panel | always-visible history panel]. (How-to-Play
    // is a centered modal dialog now, shown on first run from the constructor
    // and reopenable from Help -- not an inline panel above the board.) The
    // history panel is a frame child so it sits outside the shared XRC panel.
    history_panel_ = build_history_panel();
    wxBoxSizer *row = new wxBoxSizer(wxHORIZONTAL);
    row->Add(panel_, 1, wxEXPAND);
    row->Add(history_panel_, 0, wxEXPAND | wxTOP | wxBOTTOM | wxRIGHT, 6);
    wxBoxSizer *frame_sizer = new wxBoxSizer(wxVERTICAL);
    frame_sizer->Add(row, 1, wxEXPAND);
    SetSizer(frame_sizer);
  }

  // --- Programmatic Tier-1/Tier-3 panels (shared XRC left untouched) ---

  // Collapse the XRC panel's right-hand recipe sidebar (list + buttons);
  // recipes move to the Recipe menu. The widgets stay defined in the shared
  // XRC for the other wx UIs, so here we only hide the whole Recipes box.
  void hide_recipe_sidebar() {
    wxSizer *box = recipe_list_->GetContainingSizer();
    if (box == nullptr) {
      return;
    }
    if (auto *sb = dynamic_cast<wxStaticBoxSizer *>(box)) {
      sb->GetStaticBox()->Hide();
    }
    wxSizer *top = panel_->GetSizer();
    if (top == nullptr) {
      return;
    }
    wxSizerItem *row_item = top->GetItem(static_cast<std::size_t>(0));
    wxSizer *row = (row_item != nullptr) ? row_item->GetSizer() : nullptr;
    if (row != nullptr) {
      row->Hide(box, true);
    }
    panel_->Layout();
  }

  // Show the "How to Play" onboarding on launch unless the user chose "don't
  // show again". Called via CallAfter from the constructor, so the modal is
  // centered over a painted window.
  void maybe_show_howto() {
    if (config_->ReadBool(kConfigShowHowto, true)) {
      show_howto_dialog();
    }
  }

  // Show "How to Play" as a centered modal dialog: a heading, the rules text, a
  // small legal/illegal-move diagram, a "Don't show this again" checkbox, and a
  // "Got it" button (wxID_OK, closes the modal). Shown once on first run and
  // reopenable from Help; the goal itself lives in the status bar
  // (ui-design-principles ruling 4 -- a centered dialog, not an inline panel).
  void show_howto_dialog() {
    wxDialog dlg(this, wxID_ANY, "How to Play", wxDefaultPosition,
                 wxDefaultSize, wxDEFAULT_DIALOG_STYLE);
    wxStaticText *heading = new wxStaticText(&dlg, wxID_ANY, "How to Play");
    wxFont heading_font = heading->GetFont();
    heading_font.MakeBold();
    heading_font.SetPointSize(heading_font.GetPointSize() + 2);
    heading->SetFont(heading_font);

    wxStaticText *body = new wxStaticText(&dlg, wxID_ANY, kHowtoText);
    LegalMoveDiagram *diagram = new LegalMoveDiagram(&dlg);

    wxCheckBox *dont_show =
        new wxCheckBox(&dlg, wxID_ANY, "Don't show this again");
    dont_show->SetValue(!config_->ReadBool(kConfigShowHowto, true));
    wxButton *got_it = new wxButton(&dlg, wxID_OK, "Got it");

    wxBoxSizer *text_col = new wxBoxSizer(wxVERTICAL);
    text_col->Add(heading, 0, wxBOTTOM, 6);
    text_col->Add(body, 0);
    wxBoxSizer *top_row = new wxBoxSizer(wxHORIZONTAL);
    top_row->Add(text_col, 1, wxEXPAND | wxRIGHT, 12);
    top_row->Add(diagram, 0, wxALIGN_CENTER_VERTICAL);

    wxBoxSizer *foot_row = new wxBoxSizer(wxHORIZONTAL);
    foot_row->Add(dont_show, 0, wxALIGN_CENTER_VERTICAL);
    foot_row->AddStretchSpacer();
    foot_row->Add(got_it, 0);

    wxBoxSizer *dlg_sizer = new wxBoxSizer(wxVERTICAL);
    dlg_sizer->Add(top_row, 0, wxEXPAND | wxALL, 12);
    dlg_sizer->Add(foot_row, 0, wxEXPAND | wxLEFT | wxRIGHT | wxBOTTOM, 12);
    dlg.SetSizerAndFit(dlg_sizer);
    dlg.Centre();
    dlg.ShowModal();
    // Persist the "don't show again" choice after the dialog closes.
    config_->Write(kConfigShowHowto, !dont_show->GetValue());
    config_->Flush();
  }

  // Tier-1 always-visible move history: every move this game in the default
  // 1-2-3 (physical) labels, with a live count vs the optimal 2^N-1. Populated
  // by update_history from recorder_.moves() (hanoigui.py
  // _build_history_panel).
  wxPanel *build_history_panel() {
    wxPanel *panel = new wxPanel(this);
    const wxFont mono(wxFontInfo(12).Family(wxFONTFAMILY_TELETYPE));
    wxStaticText *title = new wxStaticText(panel, wxID_ANY, "Move history");
    wxFont title_font = title->GetFont();
    title_font.MakeBold();
    title->SetFont(title_font);
    history_header_ = new wxStaticText(panel, wxID_ANY, "");
    history_list_ = new wxListBox(panel, wxID_ANY);
    history_list_->SetFont(mono);
    const int row_h = std::max(1, history_list_->GetCharHeight());
    history_list_->SetMinSize(wxSize(240, row_h * 12 + 8));
    wxBoxSizer *sizer = new wxBoxSizer(wxVERTICAL);
    sizer->Add(title, 0, wxALL, 6);
    sizer->Add(history_header_, 0, wxLEFT | wxRIGHT | wxBOTTOM, 6);
    sizer->Add(history_list_, 1, wxEXPAND | wxLEFT | wxRIGHT | wxBOTTOM, 6);
    panel->SetSizer(sizer);
    return panel;
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

  // A disc drop resolves to physical pegs. Unlike a move button (enabled only
  // when legal), a drop can be illegal, so validate against the engine's move
  // options; legal -> the shared on_move (in current labels); illegal -> the
  // rejection reason in the status bar + a popup, then snap back (the board
  // already redrew the true state). Mirrors the wxPython
  // _on_board_drop/_on_move.
  void on_board_drop(int from_peg, int to_peg) {
    const int from_label =
        hanoi::change_labels_on_pegs(labelling_, from_peg) + 1;
    const int to_label = hanoi::change_labels_on_pegs(labelling_, to_peg) + 1;
    bool legal = false;
    for (const hanoi::Move &m : game_.move_options()) {
      if (m.from_peg == from_peg && m.to_peg == to_peg) {
        legal = true;
        break;
      }
    }
    if (legal) {
      on_move(from_label, to_label);
      return;
    }
    const std::vector<int> &from_stack =
        game_.towers()[static_cast<std::size_t>(from_peg)];
    const std::vector<int> &to_stack =
        game_.towers()[static_cast<std::size_t>(to_peg)];
    wxString reason;
    if (from_stack.empty()) {
      reason =
          wxString::Format("Peg %d is empty - nothing to move.", from_label);
    } else if (!to_stack.empty() && from_stack.back() > to_stack.back()) {
      reason = wxString::Format("Can't put disc %d on disc %d - larger on "
                                "smaller.",
                                from_stack.back(), to_stack.back());
    } else {
      reason = "Invalid move.";
    }
    set_status(reason);
    wxMessageBox(reason, "Illegal move", wxOK | wxICON_WARNING, this);
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

  // Recipe menu -> <name> -> Apply: replay the recipe under the current
  // labelling; under a relabelling, pop the three-panel rebinding teaching
  // view (hanoigui.py _apply_recipe_by_name).
  void apply_recipe_by_name(const std::string &name) {
    const hanoi::Recipe *r = registry_.get(name);
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
    set_status(wxString::Format("Applied '%s' - %d/%zu moves%s", name.c_str(),
                                applied, r->default_moves.size(),
                                err.empty() ? "." : (" - stopped: " + err)));
    if (relabelled) {
      show_rebinding(
          wxString::Format("Rebinding for '%s'", name.c_str()),
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

  // Recipe menu -> <name> -> View: show a saved recipe's steps; under a
  // relabelling, the three-panel rebinding view instead (hanoigui.py
  // _view_recipe).
  void view_recipe(const std::string &name) {
    const hanoi::Recipe *r = registry_.get(name);
    if (r == nullptr) {
      return;
    }
    if (labelling_ != hanoi::Labelling::OneTwoThree) {
      show_rebinding(
          wxString::Format("Recipe '%s' - rebinding", name.c_str()),
          "This recipe is written in labels 1, 2, 3. Under your relabelling, "
          "each move rebinds to a physical peg -- the same solution, new "
          "labels.",
          "Recipe moves", r->default_moves);
      return;
    }
    wxDialog *dlg = xrc()->LoadDialog(this, "RecipeDialog");
    dlg->SetTitle(wxString::Format("Recipe '%s'", name.c_str()));
    wxListBox *steps = XRCCTRL(*dlg, "recipe_steps", wxListBox);
    steps->SetFont(wxFont(wxFontInfo(12).Family(wxFONTFAMILY_TELETYPE)));
    const std::size_t n = r->default_moves.size();
    steps->Append(wxString::Format(
        "Recipe '%s' (%d discs, %zu moves):", name.c_str(), r->disk_count, n));
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
    rebuild_recipe_menu();
    refresh();
  }

  void on_win() {
    // Tier 2 unlocks at the first win and stays unlocked for the session
    // (feature-spec §3.5); refresh() reads the latch to enable the menus.
    won_once_ = true;
    refresh();
    const int mm = optimal_moves(game_.num_disks());
    const int mv = game_.current_moves();
    const wxString verdict =
        mv == mm
            ? "Optimal!"
            : wxString::Format("%d more than the minimum (%d).", mv - mm, mm);
    set_status(wxString::Format("Solved in %d moves - %s  Relabel pegs and "
                                "Recipe are now unlocked: save this solve, "
                                "start a bigger stack, and reuse it.",
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

  void set_graphics(bool graphics) {
    board_.set_graphics(graphics);
    board_.set_state(&game_, labelling_);
  }

  // Rebuild the Recipe menu's tail: one submenu per saved recipe (View /
  // Apply), or a disabled placeholder when none are saved. The head (Save +
  // separator, items 0-1) is kept; everything after is deleted and re-appended.
  // Mirrors hanoigui.py _rebuild_recipe_menu -- point at the recipe, not a
  // chooser verb.
  void rebuild_recipe_menu() {
    const wxMenuItemList &items = recipe_menu_->GetMenuItems();
    std::vector<wxMenuItem *> stale;
    std::size_t idx = 0;
    for (wxMenuItemList::const_iterator it = items.begin(); it != items.end();
         ++it, ++idx) {
      if (idx >= 2) {
        stale.push_back(*it);
      }
    }
    for (wxMenuItem *item : stale) {
      recipe_menu_->Delete(item);
    }
    const std::vector<std::string> names = registry_.names();
    if (names.empty()) {
      wxMenuItem *empty =
          recipe_menu_->Append(wxID_ANY, "(no saved recipes yet)");
      empty->Enable(false);
      recipe_menu_names_.clear();
      return;
    }
    for (const std::string &name : names) {
      const hanoi::Recipe *r = registry_.get(name);
      if (r == nullptr) {
        continue;
      }
      wxMenu *submenu = new wxMenu();
      wxMenuItem *view_item =
          submenu->Append(wxID_ANY, "&View", "Show this recipe's steps");
      wxMenuItem *apply_item = submenu->Append(
          wxID_ANY, "&Apply", "Replay under the current labelling");
      recipe_menu_->AppendSubMenu(
          submenu, wxString::Format("%s  (%d discs, %zu moves)", name.c_str(),
                                    r->disk_count, r->default_moves.size()));
      Bind(
          wxEVT_MENU, [this, name](wxCommandEvent &) { view_recipe(name); },
          view_item->GetId());
      Bind(
          wxEVT_MENU,
          [this, name](wxCommandEvent &) { apply_recipe_by_name(name); },
          apply_item->GetId());
    }
    recipe_menu_names_ = names;
  }

  void refresh() {
    board_.set_state(&game_, labelling_);
    const bool w = won();
    board_.set_interactive(!w); // disc dragging off once solved
    SetStatusText(wxString::Format("Moves: %d", game_.current_moves()), 2);

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
    // Tier-2 gating (dim, don't remove): the relabel items -- and the Relabel
    // and Recipe menus -- are disabled until the first win, then stay enabled.
    for (const RelabelItem &ri : relabel_items_) {
      const bool active = ri.labels[0] == cur[0] && ri.labels[1] == cur[1] &&
                          ri.labels[2] == cur[2];
      ri.item->SetItemLabel(
          (active ? wxString::FromUTF8("\xe2\x97\x8f  ") : wxString("     ")) +
          ri.base_label);
      ri.item->Enable(won_once_);
    }
    wxMenuBar *mb = GetMenuBar();
    if (relabel_menu_pos_ >= 0) {
      mb->EnableTop(static_cast<std::size_t>(relabel_menu_pos_), won_once_);
    }
    if (recipe_menu_pos_ >= 0) {
      mb->EnableTop(static_cast<std::size_t>(recipe_menu_pos_), won_once_);
    }
    recipe_save_item_->Enable(w); // can only save a won game
    // Keep the Recipe menu's submenus in sync with the registry; recipes
    // change only on save, so rebuild only when the set differs.
    if (registry_.names() != recipe_menu_names_) {
      rebuild_recipe_menu();
    }

    update_history();
    update_goal();
  }

  // Repopulate the always-visible move-history panel from the recorder: every
  // move this game in the default 1-2-3 labels, with a live count vs 2^N-1.
  void update_history() {
    if (history_list_ == nullptr || history_header_ == nullptr) {
      return;
    }
    const std::vector<std::array<int, 2>> &moves = recorder_.moves();
    history_list_->Clear();
    for (std::size_t i = 0; i < moves.size(); ++i) {
      history_list_->Append(
          wxString::Format("%zu. %d -> %d", i + 1, moves[i][0], moves[i][1]));
    }
    const std::size_t count = moves.size();
    history_header_->SetLabel(wxString::Format(
        "%zu %s  optimal %d (default 1-2-3 labels)", count,
        count == 1 ? "move" : "moves", optimal_moves(game_.num_disks())));
  }

  // The persistent goal line in the status bar (field 0) for the current disc
  // count; the full rules live in the How-to-Play panel, so this stays terse.
  void update_goal() {
    SetStatusText(
        wxString::Format("Goal: move all %d discs to peg 3", game_.num_disks()),
        0);
  }

  // --- How-to-Play panel show/hide + persistence ----------------------

  void on_toggle_history(wxCommandEvent &) {
    if (history_panel_ != nullptr) {
      history_panel_->Show(history_toggle_->IsChecked());
      Layout();
    }
  }

  void on_help_howto(wxCommandEvent &) { show_howto_dialog(); }

  void set_status(const wxString &text) { SetStatusText(text, 1); }

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

  // Tier-2 gating (feature-spec §3.5): relabel + recipes unlock at the first
  // win and stay unlocked for the rest of the session.
  bool won_once_ = false;

  wxConfigBase *config_ = nullptr;

  BoardView board_;
  wxPanel *panel_ = nullptr; // the shared XRC panel
  wxPanel *board_slot_ = nullptr;
  wxListBox *recipe_list_ = nullptr; // sidebar list, hidden (kept for the XRC)
  std::array<wxButton *, 6> move_buttons_{};
  std::vector<RelabelItem> relabel_items_;
  wxDialog *rebinding_dlg_ = nullptr;

  // Recipe menu (Tier 3) built in code; the shared XRC has no Recipe menu.
  wxMenu *recipe_menu_ = nullptr;
  wxMenuItem *recipe_save_item_ = nullptr;
  int relabel_menu_pos_ = -1;
  int recipe_menu_pos_ = -1;
  std::vector<std::string> recipe_menu_names_; // names reflected in the menu

  // Tier-1 onboarding (a modal dialog) + always-visible history, built in code.
  wxMenuItem *history_toggle_ = nullptr;
  wxPanel *history_panel_ = nullptr;
  wxStaticText *history_header_ = nullptr;
  wxListBox *history_list_ = nullptr;
};

const std::array<std::array<int, 3>, 6> HanoiFrame::kRelabelPerms{
    {{1, 2, 3}, {1, 3, 2}, {2, 1, 3}, {2, 3, 1}, {3, 1, 2}, {3, 2, 1}}};

class HanoiApp : public wxApp {
public:
  bool OnInit() override {
    // Names the per-user wxConfig store (the "show How-to-Play on launch"
    // preference) so it is stable across runs rather than keyed off argv[0].
    SetVendorName("hanoi");
    SetAppName("hanoi-wx");
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
