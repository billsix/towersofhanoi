package org.example;

public class IterativeHanoi {


    public static Move[] solveHanoiIteratively(int n, int from, int to, int temp) {
        Move[] moves = new Move[] { new Move(from, to) };

        for (int disk = 2; disk <= n; disk++) {
            int prevSize = moves.length;
            int totalSize = prevSize * 2 + 1;
            Move[] nextMoves = new Move[totalSize];

            // Copy original moves into both halves
            copyArray(moves, 0, nextMoves, 0, prevSize);
            copyArray(moves, 0, nextMoves, prevSize + 1, prevSize);

            // Middle move
            nextMoves[prevSize] = new Move(from, to);

            // Remap #1: goal → temp
            int[] remap1 = new int[4]; // 1-based
            remap1[from] = from;
            remap1[to] = temp;
            remap1[temp] = to;

            // Remap #2: source → temp, temp → goal
            int[] remap2 = new int[4];
            remap2[from] = temp;
            remap2[temp] = from;
            remap2[to] = to;

            // Apply remaps
            for (int i = 0; i < prevSize; i++) {
                nextMoves[i] = nextMoves[i].remap(remap1);
            }
            for (int i = 0; i < prevSize; i++) {
                int index = prevSize + 1 + i;
                nextMoves[index] = nextMoves[index].remap(remap2);
            }

            moves = nextMoves;
        }

        return moves;
    }

    private static void copyArray(Move[] src, int srcPos, Move[] dest, int destPos, int length) {
        for (int i = 0; i < length; i++) {
            dest[destPos + i] = src[srcPos + i];
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
