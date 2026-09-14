all: hanoi1.pdf \
     hanoi2.pdf \
     hanoi3.pdf \
     hanoi4.pdf \
     induction-workbook.pdf

# Blank, fill-in INDUCTION worksheet (one page per n=1..5) — a printable companion
# distinct from the hanoiN.svg solution diagrams. Built with pdflatex + TikZ (texlive).
induction-workbook.pdf: induction-workbook.tex
	pdflatex -interaction=nonstopmode -halt-on-error induction-workbook.tex
	rm -f induction-workbook.aux induction-workbook.log induction-workbook.out

hanoi1.pdf: hanoi1.svg
	inkscape --file=hanoi1.svg --without-gui --export-pdf=hanoi1.pdf

hanoi2.pdf: hanoi2.svg
	inkscape --file=hanoi2.svg --without-gui --export-pdf=hanoi2.pdf

hanoi3.pdf: hanoi3.svg
	inkscape --file=hanoi3.svg --without-gui --export-pdf=hanoi3.pdf


hanoi4.pdf: hanoi4.svg
	inkscape --file=hanoi4.svg --without-gui --export-pdf=hanoi4.pdf
