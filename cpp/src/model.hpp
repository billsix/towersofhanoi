// Copyright (c) 2026 William Emerison Six
//
// This program is free software; you can redistribute it and/or modify it under
// the terms of the GNU General Public License as published by the Free Software
// Foundation; either version 2 of the License, or (at your option) any later
// version.
//
// Core Towers of Hanoi game state and legal-move enumeration -- the C++ port of
// the canonical Python `hanoimodel.py` (the behaviour oracle). The three pegs
// are stacks of disk sizes; pegs are 0-indexed here (the 1-indexed labels the
// player sees are a presenter concern). Kept in sync with the Python
// feature-for-feature; do not diverge.
#pragma once

#include <array>
#include <vector>

namespace hanoi {

// A single disk move between two physical (0-indexed) pegs.
struct Move {
  int from_peg;
  int to_peg;
};

// A Towers of Hanoi game: three pegs holding stacks of disk sizes (larger
// number = larger disk; the top of a peg is the vector's last element).
class Game {
public:
  // Start with all disks on peg 0, largest at the bottom, smallest on top.
  explicit Game(int num_disks) : num_disks_{num_disks} {
    for (int size = num_disks; size > 0; --size) {
      towers_[0].push_back(size);
    }
  }

  // Whether every disk has been moved onto peg 2 (a win).
  [[nodiscard]] bool check_win_condition() const {
    return static_cast<int>(towers_[2].size()) == num_disks_;
  }

  // The currently legal moves, in the canonical peg-pair order.
  [[nodiscard]] std::vector<Move> move_options() const {
    std::vector<Move> options;
    static constexpr std::array<Move, 6> kPegPairs{
        {{0, 1}, {0, 2}, {1, 0}, {1, 2}, {2, 0}, {2, 1}}};
    for (const Move &m : kPegPairs) {
      if (is_valid_move(m.from_peg, m.to_peg)) {
        options.push_back(m);
      }
    }
    return options;
  }

  // Pop the source peg's top disk onto the destination peg and count the move.
  // Precondition: `m` is one of `move_options()`.
  void apply(const Move &m) {
    const int disk = towers_[m.from_peg].back();
    towers_[m.from_peg].pop_back();
    towers_[m.to_peg].push_back(disk);
    ++current_moves_;
  }

  [[nodiscard]] const std::array<std::vector<int>, 3> &towers() const {
    return towers_;
  }
  [[nodiscard]] int num_disks() const { return num_disks_; }
  [[nodiscard]] int current_moves() const { return current_moves_; }

private:
  // Whether the top of `from_peg` may legally move to `to_peg`.
  [[nodiscard]] bool is_valid_move(int from_peg, int to_peg) const {
    if (towers_[from_peg].empty()) { // source empty
      return false;
    }
    if (!towers_[to_peg].empty() &&
        towers_[from_peg].back() >
            towers_[to_peg].back()) { // larger on smaller
      return false;
    }
    return true;
  }

  std::array<std::vector<int>, 3> towers_{};
  int num_disks_ = 0;
  int current_moves_ = 0;
};

} // namespace hanoi
