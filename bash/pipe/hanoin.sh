#!/usr/bin/env bash

n=$1
thisScript=$0

if [ "$n" -eq 1 ]; then
    ./hanoi1.sh
    exit
fi

# move a tower, sized n-1, from tower 1 to tower 2
$thisScript $((n-1)) | tr '123' '132'
# move a tower, sized 1, from tower 1 to tower 3
$thisScript 1 | tr '123' '132'
# move a tower, sized n-1, from tower 2 to tower 3
$thisScript $((n-1)) | tr '123' '213'
