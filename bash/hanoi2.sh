#!/usr/bin/env bash

# move a tower, sized 1, from tower 1 to tower 2
./hanoi1.sh | ./1to2.sh
# move a tower, sized 1, from tower 1 to tower 3
./hanoi1.sh
# move a tower, sized 1, from tower 2 to tower 3
./hanoi1.sh | ./2to3.sh
