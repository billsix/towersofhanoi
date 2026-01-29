..
   Copyright (c) 2026 William Emerison Six

   Permission is granted to copy, distribute and/or modify this document
   under the terms of the GNU Free Documentation License, Version 1.3
   or any later version published by the Free Software Foundation;
   with no Invariant Sections, no Front-Cover Texts, and no Back-Cover Texts.

   A copy of the license is available at
   https://www.gnu.org/licenses/fdl-1.3.html.

************
Introduction
************

The Towers of Hanoi is a puzzle with three pegs and a stack of disks of different sizes.

Setup
-----

All the disks start stacked on one peg, with the largest on the bottom and smallest on top. The other two pegs are empty.

::

         |              |              |
        [*]             |              |
       [***]            |              |
      [*****]           |              |
     [*******]          |              |
    [*********]         |              |
   ==============  ==============  ==============
       Peg 1           Peg 2           Peg 3

Goal
----

Move all the disks from the starting peg to one of the other pegs.

::

         |              |                |
         |              |               [*]
         |              |              [***]
         |              |             [*****]
         |              |            [*******]
         |              |           [*********]
   ==============  ==============  ==============
       Peg 1           Peg 2           Peg 3


Rules
-----

1. Move one disk at a time
2. Only take the top disk from any peg
3. Never place a larger disk on top of a smaller disk

That's it! You keep moving disks between the three pegs, following those rules, until you've successfully moved the entire stack to a different peg.
