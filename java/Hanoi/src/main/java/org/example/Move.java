package org.example;

public class Move {
    private final int sourcePeg;
    private final int goalPeg;

    public Move(int sourcePeg, int goalPeg) {
        this.sourcePeg = sourcePeg;
        this.goalPeg = goalPeg;
    }

    public Move remap(int[] pegMap) {
        return new Move(pegMap[sourcePeg], pegMap[goalPeg]);
    }

    @Override
    public String toString() {
        return "Move from " + sourcePeg + " to " + goalPeg;
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj) return true;
        if (obj == null || getClass() != obj.getClass()) return false;
        Move other = (Move) obj;
        return sourcePeg == other.sourcePeg && goalPeg == other.goalPeg;
    }

    @Override
    public int hashCode() {
        return 31 * sourcePeg + goalPeg;
    }
}
