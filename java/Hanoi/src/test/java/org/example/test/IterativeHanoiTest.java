// Copyright (c) 2025 William Emerison Six

// This program is free software; you can redistribute it and/or
// modify it under the terms of the GNU General Public License
// as published by the Free Software Foundation; either version 2
// of the License, or (at your option) any later version.

// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.

// You should have received a copy of the GNU General Public License
// along with this program; if not, write to the Free Software
// Foundation, Inc., 59 Temple Place - Suite 330,
// Boston, MA 02111-1307, USA.

package org.example.test;

import org.example.IterativeHanoi;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

import org.example.IterativeHanoi;
import org.example.Move;

public class IterativeHanoiTest {


    @Test
    public void testOneDisk() {
        Move[] result = IterativeHanoi.solveHanoiIteratively(1);
        assertArrayEquals(new Move[] {
                new Move(1, 3)
        }, result);
    }

    @Test
    public void testTwoDisks() {
        Move[] result = IterativeHanoi.solveHanoiIteratively(2);
        assertArrayEquals(new Move[] {
                new Move(1, 2),
                new Move(1, 3),
                new Move(2, 3)
        }, result);
    }

    @Test
    public void testThreeDisks() {
        Move[] result = IterativeHanoi.solveHanoiIteratively(3);
        assertArrayEquals(new Move[] {
                new Move(1, 3),
                new Move(1, 2),
                new Move(3, 2),
                new Move(1, 3),
                new Move(2, 1),
                new Move(2, 3),
                new Move(1, 3)
        }, result);
    }
}
