package org.example.test;

import org.example.IterativeHanoi;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

import static org.example.IterativeHanoi.*;

public class IterativeHanoiTest {


    @Test
    public void testOneDisk() {
        IterativeHanoi.Move[] result = IterativeHanoi.solveHanoiIteratively(1, 1, 3, 2);
        assertArrayEquals(new IterativeHanoi.Move[] {
                new IterativeHanoi.Move(1, 3)
        }, result);
    }

    @Test
    public void testTwoDisks() {
        IterativeHanoi.Move[] result = IterativeHanoi.solveHanoiIteratively(2, 1, 3, 2);
        assertArrayEquals(new IterativeHanoi.Move[] {
                new IterativeHanoi.Move(1, 2),
                new IterativeHanoi.Move(1, 3),
                new IterativeHanoi.Move(2, 3)
        }, result);
    }

    @Test
    public void testThreeDisks() {
        IterativeHanoi.Move[] result = IterativeHanoi.solveHanoiIteratively(3, 1, 3, 2);
        assertArrayEquals(new IterativeHanoi.Move[] {
                new IterativeHanoi.Move(1, 3),
                new IterativeHanoi.Move(1, 2),
                new IterativeHanoi.Move(3, 2),
                new IterativeHanoi.Move(1, 3),
                new IterativeHanoi.Move(2, 1),
                new IterativeHanoi.Move(2, 3),
                new IterativeHanoi.Move(1, 3)
        }, result);
    }
}
