..
   Copyright (c) 2026 William Emerison Six

   Permission is granted to copy, distribute and/or modify this document
   under the terms of the GNU Free Documentation License, Version 1.3
   or any later version published by the Free Software Foundation;
   with no Invariant Sections, no Front-Cover Texts, and no Back-Cover Texts.

   A copy of the license is available at
   https://www.gnu.org/licenses/fdl-1.3.html.

***********
Solve For 2
***********

.. _2-1to3:

From 1 to 3
~~~~~~~~~~~

Follow the links below, and write down their steps

+---------------------------------------------+
|                                             |
+=============================================+
| :ref:`1 disc, from peg 1 to peg 2 <1-1to2>` |
+---------------------------------------------+
| :ref:`1 disc, from peg 1 to peg 3 <1-1to3>` |
+---------------------------------------------+
| :ref:`1 disc, from peg 2 to peg 3 <1-2to3>` |
+---------------------------------------------+

The results are the following

+------+------+
| From | To   |
+======+======+
| 1    | 2    |
+------+------+
| 1    | 3    |
+------+------+
| 2    | 3    |
+------+------+


::

       |          |          |               |          |          |
      [*]         |          |               |          |         [*]
     [***]        |          |               |          |        [***]
   =========  =========  =========  ->   =========  =========  =========
     Peg 1      Peg 2      Peg 3           Peg 1      Peg 2      Peg 3



.. _2-ItoG:


From I to G
~~~~~~~~~~~

Take :ref:`solution above <2-1to3>` - substitute variable "I" for 1, "T" for 2, "G" for 3.
"I" means initial peg, "T" means temporary peg, and "G" means goal peg.

+------+------+
| From | To   |
+======+======+
| I    | T    |
+------+------+
| I    | G    |
+------+------+
| T    | G    |
+------+------+


::

       |          |          |               |          |          |
      [*]         |          |               |          |         [*]
     [***]        |          |               |          |        [***]
   =========  =========  =========  ->   =========  =========  =========
     Peg I      Peg T      Peg G           Peg I      Peg T      Peg G



.. _2-1to2:

From 1 to 2
~~~~~~~~~~~

Take :ref:`solution from "I" to "G" <2-ItoG>` .  Substitute 1 for "I", 3 for "T", 2 for "G".



+------+------+
| From | To   |
+======+======+
| 1    | 3    |
+------+------+
| 1    | 2    |
+------+------+
| 3    | 2    |
+------+------+


::

       |          |          |               |          |          |
      [*]         |          |               |         [*]         |
     [***]        |          |               |        [***]        |
   =========  =========  =========  ->   =========  =========  =========
     Peg 1      Peg 2      Peg 3           Peg 1      Peg 2      Peg 3





.. _2-2to3:

From 2 to 3
~~~~~~~~~~~

Take :ref:`solution from "I" to "G" <2-ItoG>`.  Substitute 2 for "I", 1 for "T", 3 for "G".


+------+------+
| From | To   |
+======+======+
| 2    | 1    |
+------+------+
| 2    | 3    |
+------+------+
| 1    | 3    |
+------+------+

::

       |          |          |               |          |          |
       |         [*]         |               |          |         [*]
       |        [***]        |               |          |        [***]
   =========  =========  =========  ->   =========  =========  =========
     Peg 1      Peg 2      Peg 3           Peg 1      Peg 2      Peg 3


