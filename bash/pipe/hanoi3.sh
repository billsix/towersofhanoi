#!/usr/bin/env bash

./hanoi2.sh | tr '123' '132'
./hanoi1.sh
./hanoi2.sh | tr '123' '213'
