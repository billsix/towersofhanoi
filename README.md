Towers Of Hanoi
===============

Example implementations of towers of hanoi, implemented both using bash and using python

# Install

Runs on Linux, MacOS, and Windows using WSL2, or mingw/cygwin

## Docker/Podman

Install podman and gnu make

    make image
    make shell

Once in the shell, pick a front-end:

    hanoigame      # ncurses (text in the terminal)
    hanoi-cli      # plain stdin/stdout (good for pipes and screen readers)
    hanoi-gui      # wxPython window (needs an X display)

To run the GUI from inside the podman/docker container, mount your
X socket and forward DISPLAY when starting the shell — typically
`-e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix:Z` for Linux hosts.

Also,

    cd bash
    ./hanoi2.sh | ./fromOneToTwo.sh
    ./hanoi1.sh | ./fromOneToThree.sh
    ./hanoi2.sh | ./fromTwoToThree.sh

## Regular Python

    cd python
    python -m venv venv
    source venv/bin/activate
    python -m pip install -e .
    hanoi
