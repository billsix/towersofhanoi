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

// Tests live BESIDE the code (doctest), each TEST_CASE right after the thing it
// tests. The GUI/wasm binaries compile them out with -DDOCTEST_CONFIG_DISABLE
// (set in CMakeLists.txt), which turns every TEST_CASE into an uninstantiated
// no-op; only the `make test` executable builds and runs them. Mirrors
// python/tests/test_hanoimodel.py (the behaviour oracle).
#include <doctest/doctest.h>

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

// Game's tests sit right after the class (a TEST_CASE can't live inside a class
// body). They are inside namespace hanoi, so the types are unqualified.
TEST_CASE("a fresh game stacks every disk on peg 0, largest at the bottom") {
  const Game game{3};
  CHECK(game.towers()[0] == std::vector<int>{3, 2, 1});
  CHECK(game.towers()[1].empty());
  CHECK(game.towers()[2].empty());
  CHECK(game.num_disks() == 3);
  CHECK(game.current_moves() == 0);
  CHECK_FALSE(game.check_win_condition()); // nothing on peg 2 yet
}

TEST_CASE("check_win_condition is true once every disk reaches peg 2") {
  Game game{1};
  CHECK_FALSE(game.check_win_condition());
  game.apply(Move{0, 2}); // the only disk to the goal peg
  CHECK(game.check_win_condition());
}

TEST_CASE("move_options yields the legal moves in canonical peg-pair order") {
  const Game game{3};
  const std::vector<Move> options = game.move_options();
  REQUIRE(options.size() == 2); // off peg 0 only: to peg 1 or peg 2
  CHECK(options[0].from_peg == 0);
  CHECK(options[0].to_peg == 1);
  CHECK(options[1].from_peg == 0);
  CHECK(options[1].to_peg == 2);
}

TEST_CASE("applying moves walks the state and the legal-move set in step") {
  Game game{3};

  game.apply(game.move_options()[0]); // (0,1): smallest disk to peg 1
  CHECK(game.towers()[0] == std::vector<int>{3, 2});
  CHECK(game.towers()[1] == std::vector<int>{1});
  CHECK(game.move_options().size() == 3); // (0,2),(1,0),(1,2)

  game.apply(game.move_options()[2]); // (1,2): disk 1 to peg 2
  CHECK(game.towers()[2] == std::vector<int>{1});
  CHECK(game.move_options().size() == 3); // (0,1),(2,0),(2,1)

  game.apply(game.move_options()[0]); // (0,1): disk 2 to peg 1
  CHECK(game.towers()[0] == std::vector<int>{3});
  CHECK(game.towers()[1] == std::vector<int>{2});

  game.apply(game.move_options()[2]); // (2,1): disk 1 onto disk 2
  CHECK(game.towers()[1] == std::vector<int>{2, 1});
  CHECK(game.current_moves() == 4);
}

} // namespace hanoi
