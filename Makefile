# Build targets for the book.
# PDF: requirements-pdf.txt and Pango/fonts; legacy EPUB/HTML: pandoc.

BOOK_TITLE     := Embedded Linux on i.MX6ULL — From First Boot to First Driver
BOOK_AUTHOR    := (your name)
BOOK_DATE      := \today

# Chapter files in build order.
CHAPTERS := \
	book/part1-foundations/ch01-preface.md \
	book/part1-foundations/ch02-what-is-embedded-linux.md \
	book/part1-foundations/ch03-host-setup.md \
	book/part1-foundations/ch04-armv7a-for-mcu-engineer.md \
	book/part1-foundations/ch05-imx6ull-tour.md \
	book/part1-foundations/ch06-toolchain.md \
	book/part1-foundations/ch07-boot-rom-ivt-dcd.md \
	book/part1-foundations/ch08-board-bring-up.md

PANDOC := pandoc
PANDOC_COMMON := \
	--from=markdown+smart+pipe_tables+yaml_metadata_block \
	--toc --toc-depth=3 \
	--number-sections \
	--metadata title="$(BOOK_TITLE)" \
	--metadata author="$(BOOK_AUTHOR)" \
	--metadata date="$(BOOK_DATE)" \
	--metadata lang=en

OUT := build

.PHONY: all pdf epub html clean
all: pdf epub html

pdf:
	python -m sphinx -b html --keep-going book book/_build/html
	python tools/build_book_pdf.py

epub: $(OUT)/book.epub
$(OUT)/book.epub: $(CHAPTERS)
	@mkdir -p $(OUT)
	$(PANDOC) $(PANDOC_COMMON) -o $@ $^

html: $(OUT)/book.html
$(OUT)/book.html: $(CHAPTERS)
	@mkdir -p $(OUT)
	$(PANDOC) $(PANDOC_COMMON) --standalone --self-contained -o $@ $^

clean:
	rm -rf $(OUT)
