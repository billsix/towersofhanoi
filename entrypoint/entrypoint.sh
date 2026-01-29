#!/bin/env bash

cd /hanoi/python
python3 -m pip install -e .  --root-user-action=ignore


cd /hanoi/ && pytest --exitfirst --disable-warnings || exit

cd /hanoi/

cd /hanoi/docs
make html


# fix issues that github has for displaying the pages for me
cd _build/html/

# copy the files over
mkdir -p /output/towersofhanoi/
cp -r * /output/towersofhanoi/
# see if this fixes github issue with unscores in
# filenames created by sphinx
touch /output/modelviewprojection/.nojekyll


cd /hanoi/docs
make latexpdf
cp  build/latex/*pdf /output/towersofhanoi/

make epub
cp build/epub/*epub /output/towersofhanoi/
