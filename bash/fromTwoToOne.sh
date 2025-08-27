#!/usr/bin/env bash

exec tr '123' '231'  | python colormap.py "1=red,2=blue,3=yellow"
