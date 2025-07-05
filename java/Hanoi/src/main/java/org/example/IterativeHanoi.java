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

public class IterativeHanoi {


    public static Move[] solveHanoiIteratively(int numberOfPegs) {
        Move[] moves = new Move[] { new Move(1, 3) };

        for (int disk = 2; disk <= numberOfPegs; disk++) {
            int prevSize = moves.length;
            int totalSize = prevSize * 2 + 1;
            Move[] nextMoves = new Move[totalSize];

            // Copy original moves into both halves
            copyArray(moves, nextMoves, 0, prevSize);
            // Middle move
            nextMoves[prevSize] = new Move(1,3);
            // Copy original moves into both halves
            copyArray(moves, nextMoves, prevSize + 1, prevSize);




            // Apply remaps
            {
                // Remap #1: goal → temp
                int[] remap1 = new int[4]; // 1-based
                remap1[1] = 1;
                remap1[3] = 2;
                remap1[2] = 3;
                for (int i = 0; i < prevSize; i++) {
                    nextMoves[i] = nextMoves[i].remap(remap1);
                }
            }
            {
                // Remap #2: source → temp, temp → goal
                int[] remap2 = new int[4];
                remap2[1] = 2;
                remap2[2] = 1;
                remap2[3] = 3;

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
        Move[] moves = solveHanoiIteratively(n);
        for (Move move : moves) {
            System.out.println(move);
        }
    }
}
