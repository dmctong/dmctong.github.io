"""Merge new works from ORCID into career.yaml without duplicating.

    orcid_sync.py [--dry-run] [--file career.yaml]

A work is a duplicate when its DOI (case-insensitive) or normalized title
matches an existing publication. New works are enriched from Crossref by DOI
(full authors, journal abbreviation, volume/issue/pages) and inserted as text at
the top of `publications`, so comments and formatting elsewhere are untouched.
Existing entries are never modified. New entries get `tags: []` and
`source: orcid`; review them and add tags before committing.
"""
import argparse
import datetime as dt
import json
import re
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
UA = "career-yaml-orcid-sync/1.0"


def get_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def norm_title(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def norm_doi(s):
    return re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", (s or "").strip().lower())


def orcid_works(orcid):
    works = []
    for group in get_json(f"https://pub.orcid.org/v3.0/{orcid}/works")["group"]:
        s = group["work-summary"][0]  # ORCID's preferred version of the work
        ids = {e["external-id-type"]: e["external-id-value"]
               for e in (s.get("external-ids") or {}).get("external-id", [])}
        date = s.get("publication-date") or {}
        works.append({
            "title": s["title"]["title"]["value"],
            "doi": norm_doi(ids.get("doi")),
            "pmid": ids.get("pmid"),
            "year": int(date["year"]["value"]) if date.get("year") else None,
            "journal": (s.get("journal-title") or {}).get("value"),
        })
    return works


def as_int(s):
    return int(s) if s and str(s).isdigit() else s


def format_author(a, me):
    family, given = a.get("family", ""), a.get("given", "")
    initials = "".join(w[0].upper() for w in re.split(r"[\s.\-]+", given) if w)
    me_family, me_initials = me.split(" ", 1)
    if family == me_family and initials[:1] == me_initials[:1]:
        return me
    return f"{family} {initials}".strip() or a.get("name", "")


def crossref_entry(doi, me):
    m = get_json(f"https://api.crossref.org/works/{doi}")["message"]
    issued = (m.get("published-print") or m.get("issued"))["date-parts"][0]
    entry = {
        "authors": [format_author(a, me) for a in m.get("author", [])],
        "title": " ".join(m["title"][0].split()),
        "journal": ((m.get("short-container-title") or []) + (m.get("container-title") or [""]))[0],
        "year": issued[0],
        "month": issued[1] if len(issued) > 1 else None,
        "volume": as_int(m.get("volume")),
        "issue": as_int(m.get("issue")),
        "pages": (m.get("page") or "").replace("-", "–") or m.get("article-number"),
    }
    return entry


def make_id(entry, taken):
    journal = re.sub(r"[^a-z]", "", (entry.get("journal") or "pub").split()[0].lower())[:12] or "pub"
    words = [w for w in re.findall(r"[a-z0-9]+", entry["title"].lower())
             if w not in {"a", "an", "the", "of", "in", "for", "and", "on", "with", "to", "using"}]
    base = f"{journal}-{entry['year']}-{'-'.join(words[:2])}"
    pid, n = base, 2
    while pid in taken:
        pid, n = f"{base}-{n}", n + 1
    return pid


def render(entry):
    body = yaml.safe_dump([entry], sort_keys=False, allow_unicode=True, width=88, default_flow_style=None)
    return "".join("  " + line if line.strip() else line for line in body.splitlines(True))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default=ROOT / "career.yaml", type=Path)
    ap.add_argument("--dry-run", action="store_true", help="print new entries, don't write")
    a = ap.parse_args(argv)

    text = a.file.read_text()
    data = yaml.safe_load(text)
    orcid = data["person"]["contact"]["orcid"]
    me = data["person"]["citation_name"]
    pubs = data["publications"]
    known_dois = {norm_doi(p.get("doi")) for p in pubs if p.get("doi")}
    known_titles = {norm_title(p["title"]) for p in pubs}
    taken = {p["id"] for p in pubs}

    works = orcid_works(orcid)
    new = []
    for w in works:
        if (w["doi"] and w["doi"] in known_dois) or norm_title(w["title"]) in known_titles:
            continue
        if w["doi"]:
            try:
                entry = crossref_entry(w["doi"], me)
            except Exception as e:  # Crossref down or DOI unknown: fall back to ORCID data
                print(f"  crossref lookup failed for {w['doi']}: {e}", file=sys.stderr)
                entry = {"authors": [], "title": w["title"], "journal": w["journal"], "year": w["year"]}
        else:
            entry = {"authors": [], "title": w["title"], "journal": w["journal"], "year": w["year"]}
        entry.update(doi=w["doi"] or None, pmid=w["pmid"], status="published", tags=[], source="orcid")
        entry = {k: v for k, v in entry.items() if v not in (None, "")}
        entry = {"id": make_id(entry, taken), **entry}
        taken.add(entry["id"])
        known_titles.add(norm_title(entry["title"]))
        if w["doi"]:
            known_dois.add(w["doi"])
        new.append(entry)

    print(f"ORCID {orcid}: {len(works)} works, {len(works) - len(new)} already in {a.file.name}, {len(new)} new")
    for e in new:
        print(f"  + {e['id']}: {e['title'][:80]}")
    if not new or a.dry_run:
        return

    # Insert as text before the first existing list item so comments survive.
    lines = text.splitlines(True)
    start = next(i for i, l in enumerate(lines) if l.startswith("publications:"))
    first = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("  - ")), start + 1)
    stamp = f"  # added by orcid_sync {dt.date.today()}: review, add tags, set featured if wanted\n"
    block = stamp + "".join(render(e) for e in new)
    a.file.write_text("".join(lines[:first]) + block + "".join(lines[first:]))
    yaml.safe_load(a.file.read_text())  # fail loudly if the result isn't valid YAML
    print(f"wrote {len(new)} new publication(s) to {a.file}; review with `git diff`")


if __name__ == "__main__":
    main()
