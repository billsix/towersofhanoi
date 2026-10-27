// Copyright (c) 2026 William Emerison Six -- GNU GPL v2 or later.
//
// Peg relabelling -- the C++ port of the labelling half of the canonical Python
// `presenter.py`. The three physical pegs (0,1,2) can wear the labels 1,2,3 in
// any of six orders; colour and the shown label follow the LABEL, not the
// physical peg, so the student keeps tracking "label 1 is the blue peg" after
// relabelling. Kept in sync with the Python (the behaviour oracle); do not
// diverge. The ASCII layout maths in the Python presenter are a text-frontend
// concern and are not ported -- the ImGui GUI draws the board with primitives.
#pragma once

#include <array>
#include <optional>
#include <string> // for the labelling_name doctest

// Tests live beside the code (doctest), each right after the function it tests;
// -DDOCTEST_CONFIG_DISABLE compiles them out of the GUI/wasm binaries. Mirrors
// the labelling half of python/tests/test_presenter.py (the ASCII render maths
// are not ported to C++, so neither are their tests).
#include <doctest/doctest.h>

namespace hanoi {

// The six ways the three pegs can be labelled 1,2,3. Each names the 0-indexed
// labels worn by physical pegs 0,1,2 in order (see kLabelOrder).
enum class Labelling {
  OneTwoThree,
  OneThreeTwo,
  TwoOneThree,
  TwoThreeOne,
  ThreeOneTwo,
  ThreeTwoOne,
};

inline constexpr std::array<Labelling, 6> kAllLabellings{
    Labelling::OneTwoThree, Labelling::OneThreeTwo, Labelling::TwoOneThree,
    Labelling::TwoThreeOne, Labelling::ThreeOneTwo, Labelling::ThreeTwoOne};

// The 0-indexed label on each physical peg 0,1,2 under a labelling (mirrors
// _LABEL_ORDER).
inline constexpr std::array<int, 3> label_order(Labelling l) {
  switch (l) {
  case Labelling::OneTwoThree:
    return {0, 1, 2};
  case Labelling::OneThreeTwo:
    return {0, 2, 1};
  case Labelling::TwoOneThree:
    return {1, 0, 2};
  case Labelling::TwoThreeOne:
    return {1, 2, 0};
  case Labelling::ThreeOneTwo:
    return {2, 0, 1};
  case Labelling::ThreeTwoOne:
    return {2, 1, 0};
  }
  return {0, 1, 2};
}

// A short human label for menus, e.g. "1 2 3" / "1 3 2".
inline const char *labelling_name(Labelling l) {
  switch (l) {
  case Labelling::OneTwoThree:
    return "1 2 3";
  case Labelling::OneThreeTwo:
    return "1 3 2";
  case Labelling::TwoOneThree:
    return "2 1 3";
  case Labelling::TwoThreeOne:
    return "2 3 1";
  case Labelling::ThreeOneTwo:
    return "3 1 2";
  case Labelling::ThreeTwoOne:
    return "3 2 1";
  }
  return "1 2 3";
}

TEST_CASE("labelling_name is the short menu label") {
  CHECK(std::string{labelling_name(Labelling::OneTwoThree)} == "1 2 3");
  CHECK(std::string{labelling_name(Labelling::ThreeTwoOne)} == "3 2 1");
}

// The 0-indexed label currently attached to a physical peg.
inline int change_labels_on_pegs(Labelling l, int tower_index) {
  return label_order(l)[tower_index];
}

TEST_CASE(
    "label_order / change_labels_on_pegs give each peg's 0-indexed label") {
  CHECK(label_order(Labelling::OneTwoThree) == std::array<int, 3>{0, 1, 2});
  CHECK(label_order(Labelling::OneThreeTwo) == std::array<int, 3>{0, 2, 1});
  CHECK(change_labels_on_pegs(Labelling::OneThreeTwo, 1) == 2);
  CHECK(change_labels_on_pegs(Labelling::OneThreeTwo, 2) == 1);
}

// Which physical peg currently carries a 1-indexed label (inverse of the
// above), or nullopt if the label is out of 1..3.
inline std::optional<int> label_to_tower(Labelling l, int label) {
  if (label < 1 || label > 3) {
    return std::nullopt;
  }
  const int target = label - 1;
  const std::array<int, 3> order = label_order(l);
  for (int tower_index = 0; tower_index < 3; ++tower_index) {
    if (order[tower_index] == target) {
      return tower_index;
    }
  }
  return std::nullopt;
}

TEST_CASE("label_to_tower inverts the labelling; out-of-range is nullopt") {
  // OneThreeTwo: pegs 0,1,2 carry labels 1,3,2.
  CHECK(label_to_tower(Labelling::OneThreeTwo, 1) == 0);
  CHECK(label_to_tower(Labelling::OneThreeTwo, 3) == 1);
  CHECK(label_to_tower(Labelling::OneThreeTwo, 2) == 2);
  CHECK_FALSE(label_to_tower(Labelling::OneThreeTwo, 4).has_value());
  CHECK_FALSE(label_to_tower(Labelling::OneThreeTwo, 0).has_value());
}

// Translate a typed (from_label, to_label) 1-indexed label pair into physical
// peg indices under `l`, or nullopt if either label is out of range.
inline std::optional<std::array<int, 2>>
labels_to_towers(Labelling l, int from_label, int to_label) {
  const std::optional<int> fp = label_to_tower(l, from_label);
  const std::optional<int> tp = label_to_tower(l, to_label);
  if (!fp || !tp) {
    return std::nullopt;
  }
  return std::array<int, 2>{*fp, *tp};
}

TEST_CASE("labels_to_towers maps a label pair to physical pegs, else nullopt") {
  const std::optional<std::array<int, 2>> ok =
      labels_to_towers(Labelling::OneThreeTwo, 1, 3);
  REQUIRE(ok.has_value());
  CHECK(*ok == std::array<int, 2>{0, 1});
  CHECK_FALSE(labels_to_towers(Labelling::OneThreeTwo, 1, 9).has_value());
}

} // namespace hanoi
