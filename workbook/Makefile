all: induction-workbook.pdf

# Blank, fill-in workbook for kids (cover, worked example, one sheet per
# n=1..5, a grown-ups page, cut-out discs). Built with pdflatex + TikZ (texlive).
induction-workbook.pdf: induction-workbook.tex
	pdflatex -interaction=nonstopmode -halt-on-error induction-workbook.tex
	rm -f induction-workbook.aux induction-workbook.log induction-workbook.out
