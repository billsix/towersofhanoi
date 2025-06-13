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
