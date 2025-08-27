#!/usr/bin/env bash

exec tr '123' '213' | python colormap.py "1=yellow,2=blue,3=red"
