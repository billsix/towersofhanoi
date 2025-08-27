#!/usr/bin/env bash

exec tr '123' '321' | python colormap.py "1=red,2=yellow,3=blue"
