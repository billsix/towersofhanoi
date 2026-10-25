// Copyright (c) 2026 William Emerison Six -- GNU GPL v2 or later.
//
// Recipes -- saved sequences of moves, the C++ port of the canonical Python
// `recipe.py`. Recipes are stored in DEFAULT-label space (1-indexed physical
// peg numbers), so a recipe is independent of the labelling active when it was
// captured. At replay time the stored values are reinterpreted as labels under
// the CURRENT labelling -- the relabel-and-replay teaching moment. Kept in sync
// with the Python (the behaviour oracle); do not diverge.
#pragma once

#include "model.hpp"
#include "presenter.hpp"

#include <array>
#include <cstddef>
#include <map>
#include <optional>
#include <string>
#include <vector>

namespace hanoi {

// A saved move sequence in default-label space (each pair is 1-indexed
// from,to).
struct Recipe {
  std::string name;
  int disk_count;
  std::vector<std::array<int, 2>> default_moves;
};

// Frontend-side log of moves, in default-label space (1-indexed physical pegs).
class Recorder {
public:
  void record(int from_default, int to_default) {
    moves_.push_back({from_default, to_default});
  }
  void reset() { moves_.clear(); }
  [[nodiscard]] const std::vector<std::array<int, 2>> &moves() const {
    return moves_;
  }
  [[nodiscard]] Recipe to_recipe(const std::string &name,
                                 int disk_count) const {
    return Recipe{name, disk_count, moves_};
  }

private:
  std::vector<std::array<int, 2>> moves_;
};

// In-memory recipe store keyed by name (std::map keeps names() sorted, like the
// Python).
class RecipeRegistry {
public:
  void save(const Recipe &r) { by_name_[r.name] = r; }
  [[nodiscard]] const Recipe *get(const std::string &name) const {
    const auto it = by_name_.find(name);
    return it == by_name_.end() ? nullptr : &it->second;
  }
  [[nodiscard]] std::vector<std::string> names() const {
    std::vector<std::string> out;
    for (const auto &kv : by_name_) {
      out.push_back(kv.first);
    }
    return out;
  }
  [[nodiscard]] std::size_t size() const { return by_name_.size(); }

private:
  std::map<std::string, Recipe> by_name_;
};

// One replayed move's outcome.
struct StepResult {
  int from_label;
  int to_label;
  std::optional<int> from_peg;
  std::optional<int> to_peg;
  std::optional<std::string> error;
  [[nodiscard]] bool ok() const { return !error.has_value(); }
};

namespace detail {
inline std::string explain_illegal(const Game &game, int from_peg, int to_peg,
                                   int from_label, int to_label) {
  const std::string step = "recipe move '" + std::to_string(from_label) +
                           " -> " + std::to_string(to_label) + "'";
  if (game.towers()[from_peg].empty()) {
    return step + ": peg " + std::to_string(from_label) + " (physical " +
           std::to_string(from_peg + 1) + ") is empty.";
  }
  if (!game.towers()[to_peg].empty() &&
      game.towers()[from_peg].back() > game.towers()[to_peg].back()) {
    return step + ": would put a larger disc on a smaller one.";
  }
  return step + ": illegal in current state.";
}
} // namespace detail

// Replay `recipe` against `game` under `labelling`, reinterpreting the stored
// default-space values as labels under `labelling`. Stops after the first
// failure (like the Python). No disk-count check -- a small recipe may
// legitimately apply to a larger game.
inline std::vector<StepResult> apply(const Recipe &recipe, Game &game,
                                     Labelling labelling) {
  std::vector<StepResult> results;
  for (const std::array<int, 2> &mv : recipe.default_moves) {
    const int from_label = mv[0];
    const int to_label = mv[1];
    const std::optional<std::array<int, 2>> physical =
        labels_to_towers(labelling, from_label, to_label);
    if (!physical) {
      results.push_back({from_label, to_label, std::nullopt, std::nullopt,
                         "Recipe move '" + std::to_string(from_label) + " -> " +
                             std::to_string(to_label) +
                             "' uses a label that doesn't exist under the "
                             "current labelling."});
      return results;
    }
    const int fp = (*physical)[0];
    const int tp = (*physical)[1];
    bool legal = false;
    for (const Move &m : game.move_options()) {
      if (m.from_peg == fp && m.to_peg == tp) {
        legal = true;
        break;
      }
    }
    if (!legal) {
      results.push_back(
          {from_label, to_label, fp, tp,
           detail::explain_illegal(game, fp, tp, from_label, to_label)});
      return results;
    }
    game.apply(Move{fp, tp});
    results.push_back({from_label, to_label, fp, tp, std::nullopt});
  }
  return results;
}

// Map each recipe label 1..3 to the 1-indexed physical peg it resolves to under
// `labelling` (identity under OneTwoThree). Used to SHOW the label->peg
// rebinding.
inline std::array<std::array<int, 2>, 3> rebinding(Labelling labelling) {
  std::array<std::array<int, 2>, 3> pairs{};
  for (int i = 0; i < 3; ++i) {
    const int label = i + 1;
    const std::optional<int> peg = label_to_tower(labelling, label);
    pairs[i] = {label, *peg + 1}; // a label in 1..3 always resolves
  }
  return pairs;
}

} // namespace hanoi
