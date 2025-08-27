#!/usr/bin/env bash

exec tr '123' '312' | python colormap.py "1=yellow,2=red,3=blue"
