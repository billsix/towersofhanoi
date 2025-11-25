#!/usr/bin/env bash

n=$1
if [ "$n" -eq 1 ]; then
    ./hanoi1.sh
    exit
fi

# move a tower, sized n-1, from tower 1 to tower 2
./hanoin.sh $((n-1)) | ./1to2.sh
# move a tower, sized 1, from tower 1 to tower 3
./hanoin.sh 1
# move a tower, sized n-1, from tower 2 to tower 3
./hanoin.sh $((n-1)) | ./2to3.sh
