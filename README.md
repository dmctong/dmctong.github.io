# career.yaml

One data file, every professional document: resume variants, a full academic CV,
and a personal website.

```
career.yaml               the only file you edit
variants/*.yaml           one resume per file: sections, tag filters, order
templates/                Typst layouts (resume.typ, cv.typ, shared common.typ)
site/                     static site generator + stylesheet
scripts/career.py         resolves career.yaml + a variant into a document model
scripts/orcid_sync.py     merges new ORCID works into career.yaml
```

## Usage

```sh
make            # everything → build/
make resumes    # build/resume-<variant>.pdf (fails if over the variant's max_pages)
make cv         # build/cv.pdf
make site       # build/site/ (index.html + PDFs)
make serve      # preview at http://localhost:8000
make orcid      # pull new publications from ORCID, then review `git diff`
```

Requirements: Python 3 with `pip install -r requirements.txt`, and
[Typst](https://github.com/typst/typst/releases) 0.14.2 on your PATH.

## Editing

- **Tags** are defined in `tag_vocabulary` at the top of `career.yaml`. Variants
  filter bullets, publications, and talks by tag.
- **Counts** in text (`{N_pubs}`, `{n_journals}`, `{reviews}`, `{year_range}`) are
  computed at build time, so "Eleven peer-reviewed publications" stays correct.
- **A new resume variant** is a new file in `variants/`. Copy `director.yaml` and
  change the section list and filters. `make` picks it up automatically.
- **Presentations** dated in the future render as "(upcoming)" until they pass.

## Privacy

This repo is public. Keep salary, applications, recruiter notes, phone number,
and address out of it. Files matching `*.private.*` or `private/` are git-ignored.

## Deploying

Pushing to `main` runs `.github/workflows/pages.yml`, which builds everything
and publishes `build/site` to GitHub Pages. Enable it once under
Settings → Pages → Source: GitHub Actions.
