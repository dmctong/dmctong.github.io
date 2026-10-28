# Edit career.yaml, then `make` (or `make all`). Outputs land in build/.
#   make resumes   one PDF per variants/*.yaml   -> build/resume-<name>.pdf
#   make cv        full academic CV              -> build/cv.pdf
#   make site      static site (+ PDFs)          -> build/site/ (plain page at resume/)
#   make orcid     merge new ORCID works into career.yaml (then review the diff)
#   make serve     preview the site at http://localhost:8000

PY     ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
TYPST  ?= typst
TYPSTC  = $(TYPST) compile --root . --ignore-system-fonts

VARIANTS := $(basename $(notdir $(wildcard variants/*.yaml)))
RESUMES  := $(VARIANTS:%=build/resume-%.pdf)
MODEL    := career.yaml scripts/career.py
TYP      := templates/common.typ

.PHONY: all resumes cv site orcid serve clean
.SECONDARY:  # keep the intermediate JSON models for inspection

all: resumes cv site

resumes: $(RESUMES)
cv: build/cv.pdf
site: build/site/index.html

build/resume-%.json: variants/%.yaml $(MODEL)
	$(PY) scripts/career.py resolve $< -o $@

build/%.json: $(MODEL)
	$(PY) scripts/career.py resolve $* -o $@

build/resume-%.pdf: build/resume-%.json templates/resume.typ $(TYP)
	$(TYPSTC) --input data=/$< templates/resume.typ $@
	$(PY) scripts/career.py check-pages $@ $<

build/cv.pdf: build/cv.json templates/cv.typ $(TYP)
	$(TYPSTC) --input data=/$< templates/cv.typ $@

build/site/index.html: build/site.json site/build.py site/style.css site/classic.py site/classic.css $(wildcard site/headshot.jpg) build/cv.pdf $(RESUMES)
	$(PY) site/build.py $< build/site

orcid:
	$(PY) scripts/orcid_sync.py

serve: site
	$(PY) -m http.server -d build/site 8000

clean:
	rm -rf build
