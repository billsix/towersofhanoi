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

package org.example;

public class Move {
    private final int thisMovesSourcePeg;
    private final int thisMovesGoalPeg;

    public Move(int sourcePeg, int goalPeg) {
        this.thisMovesSourcePeg = sourcePeg;
        this.thisMovesGoalPeg = goalPeg;
    }

    public Move remap(int[] renumberingContext) {
        return new Move(renumberingContext[thisMovesSourcePeg], renumberingContext[thisMovesGoalPeg]);
    }

    @Override
    public String toString() {
        return "Move from " + thisMovesSourcePeg + " to " + thisMovesGoalPeg;
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj) return true;
        if (obj == null || getClass() != obj.getClass()) return false;
        Move other = (Move) obj;
        return thisMovesSourcePeg == other.thisMovesSourcePeg && thisMovesGoalPeg == other.thisMovesGoalPeg;
    }

    @Override
    public int hashCode() {
        return 31 * thisMovesSourcePeg + thisMovesGoalPeg;
    }
}
