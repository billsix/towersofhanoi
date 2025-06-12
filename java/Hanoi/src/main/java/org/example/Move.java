package org.example;

public class Move {
    private final int from;
    private final int to;

    public Move(int from, int to) {
        this.from = from;
        this.to = to;
    }

    public Move remap(int[] pegMap) {
        return new Move(pegMap[from], pegMap[to]);
    }

    @Override
    public String toString() {
        return "Move from " + from + " to " + to;
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj) return true;
        if (obj == null || getClass() != obj.getClass()) return false;
        Move other = (Move) obj;
        return from == other.from && to == other.to;
    }

    @Override
    public int hashCode() {
        return 31 * from + to;
    }
}
