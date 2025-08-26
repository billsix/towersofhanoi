#!/usr/bin/env bash

# move a tower, sized 2, from tower 1 to tower 2
./hanoi2.sh | ./fromOneToTwo.sh
# move a tower, sized 1, from tower 1 to tower 3
./hanoi1.sh
# move a tower, sized 2, from tower 2 to tower 3
./hanoi2.sh | ./fromTwoToThree.sh
