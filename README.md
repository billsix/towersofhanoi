Towers Of Hanoi
===============

Example implementations of towers of hanoi, implemented both using bash and using python

# Install

Runs on Linux, MacOS, and Windows using WSL2, or mingw/cygwin

## Docker/Podman

Install podman and gnu make

    make image
    make shell

Once in the shell,

    hanoigame

Also,

    cd ../bash
    ./hanoi2.sh | ./fromOneToTwo.sh
    ./hanoi1.sh | ./fromOneToThree.sh
    ./hanoi2.sh | ./fromTwoToThree.sh

## Regular Python

    cd python
    python -m venv venv
    source venv/bin/activate
    python -m pip install -e .
    hanoi
