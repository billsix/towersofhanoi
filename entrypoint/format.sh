#!/bin/env bash

cd /hanoi

ruff check . --fix
ruff format --line-length=80

