package org.example;

public class IterativeHanoi {


    public static Move[] solveHanoiIteratively(int numberOfPegs, int sourcePeg, int goalPeg, int temporaryPeg) {
        Move[] moves = new Move[] { new Move(sourcePeg, goalPeg) };

        for (int disk = 2; disk <= numberOfPegs; disk++) {
            int prevSize = moves.length;
            int totalSize = prevSize * 2 + 1;
            Move[] nextMoves = new Move[totalSize];

            // Copy original moves into both halves
            copyArray(moves, nextMoves, 0, prevSize);
            // Middle move
            nextMoves[prevSize] = new Move(sourcePeg, goalPeg);
            // Copy original moves into both halves
            copyArray(moves, nextMoves, prevSize + 1, prevSize);




            // Apply remaps
            {
                // Remap #1: goal → temp
                int[] remap1 = new int[4]; // 1-based
                remap1[sourcePeg] = sourcePeg;
                remap1[goalPeg] = temporaryPeg;
                remap1[temporaryPeg] = goalPeg;
                for (int i = 0; i < prevSize; i++) {
                    nextMoves[i] = nextMoves[i].remap(remap1);
                }
            }
            {
                // Remap #2: source → temp, temp → goal
                int[] remap2 = new int[4];
                remap2[sourcePeg] = temporaryPeg;
                remap2[temporaryPeg] = sourcePeg;
                remap2[goalPeg] = goalPeg;

                for (int i = 0; i < prevSize; i++) {
                    int index = prevSize + 1 + i;
                    nextMoves[index] = nextMoves[index].remap(remap2);
                }
            }

            moves = nextMoves;
        }

        return moves;
    }

    private static void copyArray(Move[] src, Move[] dest, int destPos, int length) {
        for (int i = 0; i < length; i++) {
            dest[destPos + i] = src[i];
        }
    }

    public static void main(String[] args) {
        int n = 3;
        Move[] moves = solveHanoiIteratively(n, 1, 3, 2);
        for (Move move : moves) {
            System.out.println(move);
        }
    }
}
