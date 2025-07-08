#!/usr/bin/env bash

# move a tower, sized 2, from tower 1 to tower 2
./hanoi3.sh | tr '23' '32'
# move a tower, sized 1, from tower 1 to tower 3
./hanoi1.sh
# move a tower, sized 3, from tower 2 to tower 3
./hanoi3.sh | tr '12' '21'
