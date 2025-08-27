#!/usr/bin/env bash

exec tr '123' '123' | python colormap.py "1=blue,2=yellow,3=red"
