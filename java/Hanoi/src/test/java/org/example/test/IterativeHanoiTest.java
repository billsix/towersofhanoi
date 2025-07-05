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
