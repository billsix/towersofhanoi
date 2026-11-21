#!/bin/bash
# Start the Rust wx GUI under Xvfb, click through to the View menu, and
# screenshot the root window to /out/$1-*.png. Clicks are screen coordinates
# read from an earlier screenshot (1200x750 screen).
export DISPLAY=:77
Xvfb :77 -screen 0 1200x750x24 >/dev/null 2>&1 &
sleep 2
/hanoi-rust/.container-target/debug/hanoi-gui >/tmp/gui.log 2>&1 &
sleep 5
xdotool mousemove 936 463 click 1; sleep 1     # How to Play: Got it
xdotool mousemove 306 59 click 1; sleep 1      # View menu
xdotool mousemove 380 86; sleep 1              # Board Style submenu
xdotool mousemove 535 86 click 1; sleep 1       # Text
xdotool mousemove 215 622 click 1; sleep 1      # move 1 -> 2
xdotool mousemove 215 660 click 1; sleep 1      # move 1 -> 3
import -window root "/out/$1-text.png"
xdotool mousemove 980 147 click 1; sleep 1      # history row 1
import -window root "/out/$1-review.png"
