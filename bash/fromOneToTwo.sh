#!/usr/bin/env bash

exec tr '123' '132'  | python colormap.py "1=blue,2=red,3=yellow"
