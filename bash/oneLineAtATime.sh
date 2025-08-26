#!/usr/bin/env bash

mapfile -t lines

for line in "${lines[@]}"; do
    echo "$line"
    read -p "Press Enter for the next line" < /dev/tty
done
