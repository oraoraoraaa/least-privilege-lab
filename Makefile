SOURCES := $(wildcard src/main/java/leastprivilege/*.java)
JAR := build/least-privilege-lab.jar

.PHONY: build demo test
build: $(JAR)

$(JAR): $(SOURCES) Makefile
	mkdir -p build/classes
	javac --release 17 -encoding UTF-8 -d build/classes $(SOURCES)
	jar --create --file $@ --main-class leastprivilege.Main -C build/classes .

demo: $(JAR)
	java -jar $(JAR) review examples/registry/grants.tsv examples/registry/events.tsv

test: $(JAR)
	sh tests/review.sh $(JAR)

.PHONY: guidebook
GUIDE := docs/guidebook/guidebook
PDFLATEX := pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build/guidebook
guidebook:
	mkdir -p build/guidebook
	$(PDFLATEX) $(GUIDE).tex
	$(PDFLATEX) $(GUIDE).tex
	cp build/guidebook/guidebook.pdf $(GUIDE).pdf

.PHONY: paper
paper:
	uv run --locked --script paper/figures.py
	mkdir -p build/paper
	@set -e; for pass in 1 2 3 4 5; do \
		pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build/paper paper/paper.tex; \
		if ! grep -Eiq 'rerun to get|rerun LaTeX|undefined (references|citations)' build/paper/paper.log; then break; fi; \
		if [ "$$pass" = 5 ]; then echo 'Paper references did not converge' >&2; exit 1; fi; \
	done
	cp build/paper/paper.pdf paper/paper.pdf
