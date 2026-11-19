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
