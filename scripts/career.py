"""Resolve career.yaml (+ a variant) into a render-ready document model.

The model is shared by the Typst templates (as JSON) and the site generator:

    {"person": {...}, "generated": "October 2026", "max_pages": 2,
     "sections": [{"id", "title", "kind", ...}]}

Section kinds
    paragraph  {"text": rich}
    entries    {"entries": [{"lines": [{"left": rich, "right": str}],
                             "description": str | None, "bullets": [rich]}]}
    list       {"intro": rich | None, "items": [rich], "numbered": bool, "note": rich | None}

Rich text is a list of runs: {"text": str, "bold"?: bool, "italic"?: bool, "link"?: url}.

Usage
    career.py resolve variants/director.yaml -o build/resume-director.json
    career.py resolve cv   -o build/cv.json
    career.py resolve site -o build/site.json
    career.py check-pages build/resume-director.pdf build/resume-director.json
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MONTHS = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]
WORDS = ("zero one two three four five six seven eight nine ten eleven twelve thirteen "
         "fourteen fifteen sixteen seventeen eighteen nineteen twenty").split()
TODAY = dt.date.today()

TITLES = {
    "summary": "Profile",
    "experience": "Professional Experience",
    "service": "Leadership & Service",
    "peer_review": "Peer Review",
    "publications": "Publications",
    "presentations": "Presentations",
    "skills": "Skills and Expertise",
    "education": "Education",
    "awards": "Awards",
}

# The CV is "everything"; the site is everything, ordered for the web.
PDF_CONTACTS = ["location", "email", "website", "linkedin", "orcid"]  # site links GitHub
CV = {"contacts": PDF_CONTACTS, "sections": [
    "summary", "experience", "service", {"id": "peer_review", "style": "list"}, "skills",
    "education", {"id": "publications", "numbered": True, "show_ids": True},
    "presentations", "awards"]}
SITE = {"sections": [
    "summary", "experience", "service", {"id": "publications", "show_ids": True},
    "presentations", {"id": "peer_review", "style": "list"}, "education", "awards", "skills"],
    # file: build output; publish_as: the name visitors see and download
    "downloads": [{"label": "CV (PDF)", "file": "cv.pdf", "publish_as": "Dominic-Tong-CV.pdf"},
                  {"label": "Resume (PDF)", "file": "resume-director.pdf",
                   "publish_as": "Dominic-Tong-Resume.pdf"}]}


# ------------------------------------------------------------------ helpers
def load(path=ROOT / "career.yaml"):
    return yaml.safe_load(Path(path).read_text())


def clean(s):
    """Collapse whitespace; forbid line breaks inside slashed terms like ISoP/ACCP."""
    return re.sub(r"(?<=\w)/(?=\w)", "/\u2060", " ".join(str(s).split()))


def t(text, **style):
    return {"text": text, **style}


def number_word(n, cap=False):
    w = WORDS[n] if n < len(WORDS) else str(n)
    return w[0].upper() + w[1:] if cap else w


def parse_date(d):
    """'2025-01' | 2025 | 'present' | None -> (year, month | None) or None."""
    if d in (None, "present"):
        return None
    year, _, month = str(d).partition("-")
    return int(year), int(month) if month else None


def sort_key(d):
    p = parse_date(d)
    return (9999, 12) if d == "present" else (p[0], p[1] or 0) if p else (0, 0)


def fmt_date(d):
    if d == "present":
        return "present"
    p = parse_date(d)
    if not p:
        return ""
    return f"{MONTHS[p[1] - 1]} {p[0]}" if p[1] else str(p[0])


def fmt_range(start, end):
    s, e = parse_date(start), parse_date(end)
    if s and e and s[0] == e[0]:
        if s[1] and e[1]:  # "June – Dec. 2019"
            return f"{MONTHS[s[1] - 1]} – {MONTHS[e[1] - 1]} {e[0]}"
        return str(e[0])
    return f"{fmt_date(start)} – {fmt_date(end)}"


def is_future(d):
    p = parse_date(d)
    return bool(p) and (p[0], p[1] or 1) > (TODAY.year, TODAY.month)


def counts(data):
    pubs = [p for p in data["publications"] if p.get("status", "published") == "published"]
    reviews = data["peer_review"]["entries"]
    years = sorted({y for e in reviews for y in e["years"]})
    return {
        "pubs": len(pubs),
        "journals": len(reviews),
        "reviews": sum(e.get("reviews", 1) for e in reviews),
        "year_range": f"{years[0]}–{years[-1]}" if len(years) > 1 else str(years[0]),
        "review_status": "completed or in progress"
        if any(e.get("status") == "in-progress" for e in reviews) else "completed",
    }


def fill(template, c):
    """{n_pubs} -> 'eleven', {N_pubs} -> 'Eleven', {year_range} -> '2025–2026'."""
    def sub(m):
        if m.group(1):
            return number_word(c[m.group(2)], cap=m.group(1) == "N")
        return str(c[m.group(3)])
    return re.sub(r"\{([nN])_(\w+)\}|\{(\w+)\}", sub, clean(template))


def merge_runs(runs):
    out = []
    for r in runs:
        if out and set(r) == {"text"} and set(out[-1]) == {"text"}:
            out[-1] = t(out[-1]["text"] + r["text"])
        else:
            out.append(r)
    return out


def end_sentence(s):
    s = clean(s)
    return s if s[-1] in ".?!" else s + "."


# ---------------------------------------------------------------- citations
def author_runs(authors, me, max_authors=None, et_al=False):
    shown = list(authors)
    if max_authors and len(authors) > max_authors:
        shown = authors[:max_authors]
        if me in authors and me not in shown:
            shown += ["…", me]
        et_al = True
    runs = []
    for i, a in enumerate(shown):
        if i:
            runs.append(t(", "))
        runs.append(t(a, bold=True) if a == me else t(a))
    if et_al:
        runs.append(t(", et al"))
    return runs


def cite_publication(p, me, max_authors=None, show_ids=False):
    runs = author_runs(p["authors"], me, max_authors, p.get("et_al", False))
    runs.append(t(". " + end_sentence(p["title"]) + " "))
    runs.append(t(p["journal"], italic=True))
    loc = str(p["year"])
    if p.get("volume"):
        loc += f";{p['volume']}"
        if p.get("issue"):
            loc += f"({p['issue']})"
    if p.get("pages"):
        loc += f":{p['pages']}"
    runs.append(t(f". {loc}."))
    if p.get("doi"):
        runs += [t(" "), t(f"doi:{p['doi']}", link=f"https://doi.org/{p['doi']}")]
    if show_ids and p.get("pmid"):
        runs.append(t(f" PMID: {p['pmid']}" + (f"; PMCID: {p['pmcid']}" if p.get("pmcid") else "") + "."))
    if p.get("status", "published") != "published":
        runs.append(t(f" ({p['status']})", italic=True))
    return merge_runs(runs)


def cite_presentation(x, me, max_authors=None):
    kind = {"poster": "Poster", "oral": "Oral presentation"}.get(x.get("type"))
    runs = []
    if x.get("status") == "upcoming" or is_future(x["date"]):
        runs.append(t("(upcoming) ", italic=True))
    runs += author_runs(x["authors"], me, max_authors)
    title = end_sentence(x["title"]) if x.get("title") else ""
    if x.get("presenter"):  # someone else gave the talk
        kind = f"{kind}; presented by {x['presenter']}" if kind else f"Presented by {x['presenter']}"
    if kind:
        title = (title[:-1] + f" ({kind})." if title else f"{kind}.")
    runs.append(t(". " + title + " "))
    runs.append(t(x["venue"], italic=True))
    runs.append(t(f", {x['location']}. {fmt_date(x['date'])}."))
    return merge_runs(runs)


# ------------------------------------------------------------------ sections
def select_bullets(bullets, opts):
    inc_tags, inc_ids = set(opts.get("include_tags", [])), set(opts.get("include_ids", []))
    exclude = set(opts.get("exclude_ids", []))
    keep = [b for b in bullets
            if b.get("id") not in exclude
            and (not (inc_tags or inc_ids) or b.get("id") in inc_ids or inc_tags & set(b.get("tags", [])))]
    priority = opts.get("tag_priority", [])
    if priority:
        rank = lambda b: min((priority.index(tg) for tg in b.get("tags", []) if tg in priority),
                             default=len(priority))
        keep.sort(key=rank)  # stable: ties keep file order
    pins = opts.get("pin_ids", [])
    if pins:  # pinned bullets go first, in the order listed
        keep.sort(key=lambda b: pins.index(b["id"]) if b.get("id") in pins else len(pins))
    if opts.get("max_bullets"):
        keep = keep[: opts["max_bullets"]]
    return keep


def org_entry(item, opts, bold_org=True):
    """Shared shape for positions and service roles."""
    roles = item["roles"]
    if item.get("id") in opts.get("condensed", []):
        span = fmt_range(roles[-1]["start"], roles[0]["end"])
        return {"lines": [{"left": [t(roles[0]["title"], bold=True), t(", " + item["org"])], "right": span}],
                "description": None, "bullets": []}
    lines = [{"left": [t(r["title"], bold=(i == 0))], "right": fmt_range(r["start"], r["end"])}
             for i, r in enumerate(roles)]
    org = [t(item["org"], bold=bold_org)]
    if item.get("location"):
        org.append(t(" — " + item["location"]))
    lines.append({"left": org, "right": ""})
    bullets = select_bullets(item.get("bullets", []), opts)
    desc = item.get("description") if opts.get("descriptions", True) else None
    return {"lines": lines, "description": clean(desc) if desc else None,
            "bullets": [[t(clean(b["text"]))] for b in bullets]}


def build_section(sid, opts, data, c):
    me = data["person"]["citation_name"]
    title = opts.get("title", TITLES[sid])
    sec = {"id": sid, "title": title}

    if sid == "summary":
        key = opts.get("key", "default")
        return {**sec, "kind": "paragraph", "text": [t(fill(data["summary"][key], c))]}

    if sid in ("experience", "service"):
        items = data["positions" if sid == "experience" else "service"]
        items = [i for i in items if i["id"] not in opts.get("exclude", [])]
        return {**sec, "kind": "entries",
                "entries": [org_entry(i, opts, bold_org=(sid == "experience")) for i in items]}

    if sid == "education":
        entries = []
        for e in data["education"]:
            bullets = [[t(clean(n))] for n in e.get("notes", [])][: opts.get("max_bullets")]
            if e.get("thesis") and opts.get("thesis", True):
                bullets.append([t("Thesis: "), t(clean(e["thesis"]), italic=True)])
            entries.append({"lines": [{"left": [t(e["degree"], bold=True)], "right": fmt_date(e["date"])},
                                      {"left": [t(e["institution"])], "right": ""}],
                            "description": None, "bullets": bullets})
        return {**sec, "kind": "entries", "entries": entries}

    if sid == "awards":
        entries = [{"lines": [{"left": [t(a["name"], bold=True)], "right": str(a["year"])},
                              {"left": [t(a["org"])], "right": ""}],
                    "description": None,
                    "bullets": [[t(clean(a["description"]))]] if a.get("description") and opts.get("max_bullets", 1) else []}
                   for a in data["awards"]]
        return {**sec, "kind": "entries", "entries": entries}

    if sid == "skills":
        items = [[t(g["group"] + ": ", bold=True), t(", ".join(g["items"]))] for g in data["skills"]]
        return {**sec, "kind": "list", "intro": None, "items": items, "numbered": False, "note": None}

    if sid == "peer_review":
        pr = data["peer_review"]
        if opts.get("style", "line") == "line":
            names = [e["journal"] for e in pr["entries"][: opts.get("highlight", 3)]]
            template = opts.get("text", "Invited reviewer for {journals} international journals "
                                        "({reviews} reviews, {year_range}), including {highlights}.")
            highlights = ", ".join(names[:-1]) + ", and " + names[-1] if len(names) > 1 else "".join(names)
            text = fill(template.replace("{highlights}", highlights), c)
            return {**sec, "kind": "paragraph", "text": [t(text)]}
        items = []
        for e in pr["entries"]:
            ys = e["years"]
            when = f"{ys[0]}–{ys[-1]}" if len(ys) > 1 else str(ys[0])
            extra = e.get("reviews", 1) - 1
            if extra:
                when += f", incl. {number_word(extra)} re-review" + ("s" if extra > 1 else "")
            if e.get("status") == "in-progress":
                when += ", in progress"
            run = [t(e["journal"], italic=True), t(f" ({when})")]
            if e.get("note"):
                run.append(t(" — " + e["note"]))
            items.append(merge_runs(run))
        return {**sec, "kind": "list", "intro": [t(fill(pr["intro"], c))], "items": items,
                "numbered": False, "note": None}

    if sid == "publications":
        pubs = data["publications"]
        select = opts.get("select", [])
        select = [select] if isinstance(select, str) else select
        if select:  # union of: featured, first_author
            pubs = [p for p in pubs
                    if ("featured" in select and p.get("featured"))
                    or ("first_author" in select and p["authors"][:1] == [me])]
        if opts.get("include_tags"):
            pubs = [p for p in pubs if set(opts["include_tags"]) & set(p.get("tags", []))]
        pubs = [p for p in pubs if p["id"] not in opts.get("exclude_ids", [])]
        pubs = sorted(pubs, key=lambda p: (p["year"], p.get("month", 0)), reverse=True)
        items = [cite_publication(p, me, opts.get("max_authors"), opts.get("show_ids", False)) for p in pubs]
        note = [t(fill(opts["note"], c), italic=True)] if opts.get("note") else None
        return {**sec, "kind": "list", "intro": None, "items": items,
                "numbered": opts.get("numbered", False), "note": note}

    if sid == "presentations":
        talks = sorted(data["presentations"], key=lambda x: sort_key(x["date"]), reverse=True)
        if opts.get("include_tags"):
            talks = [x for x in talks if set(opts["include_tags"]) & set(x.get("tags", []))]
        talks = [x for x in talks if x["id"] not in opts.get("exclude_ids", [])]
        if opts.get("max_items"):
            talks = talks[: opts["max_items"]]
        items = [cite_presentation(x, me, opts.get("max_authors")) for x in talks]
        return {**sec, "kind": "list", "intro": None, "items": items,
                "numbered": opts.get("numbered", False), "note": None}

    raise SystemExit(f"unknown section: {sid}")


def person(data, keys=None):
    """keys: contact fields to show, in fixed order; None shows all."""
    p = data["person"]
    c = {k: v for k, v in p["contact"].items() if keys is None or k in keys}
    location = p.get("location") if keys is None or "location" in keys else None
    contacts = []
    if location:
        contacts.append(t(location))
    if c.get("email"):
        contacts.append(t(c["email"], link=f"mailto:{c['email']}"))
    if c.get("website"):
        contacts.append(t(re.sub(r"^https?://", "", c["website"]).rstrip("/"), link=c["website"]))
    if c.get("linkedin"):
        contacts.append(t(f"linkedin.com/in/{c['linkedin']}", link=f"https://www.linkedin.com/in/{c['linkedin']}"))
    if c.get("orcid"):
        contacts.append(t(f"ORCID {c['orcid']}", link=f"https://orcid.org/{c['orcid']}"))
    if c.get("github"):
        contacts.append(t(f"github.com/{c['github']}", link=f"https://github.com/{c['github']}"))
    if c.get("google_scholar"):
        contacts.append(t("Google Scholar", link=f"https://scholar.google.com/citations?user={c['google_scholar']}"))
    return {"name": p["name"], "credentials": p.get("credentials"), "headline": p.get("headline"),
            "contacts": [[run] for run in contacts]}


def resolve(config, data):
    c = counts(data)
    sections = []
    for s in config["sections"]:
        sid, opts = (s, {}) if isinstance(s, str) else (s["id"], s)
        sections.append(build_section(sid, opts, data, c))
    return {"person": person(data, config.get("contacts")), "generated": f"{TODAY.strftime('%B')} {TODAY.year}",
            "max_pages": config.get("max_pages"), "downloads": config.get("downloads", []),
            "sections": sections}


# ---------------------------------------------------------------------- cli
def pdf_pages(path):
    return len(re.findall(rb"/Type\s*/Page\b(?!s)", Path(path).read_bytes()))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("resolve")
    r.add_argument("config", help="variants/<name>.yaml, 'cv', or 'site'")
    r.add_argument("-o", "--out", required=True)
    r.add_argument("--data", default=ROOT / "career.yaml")
    k = sub.add_parser("check-pages")
    k.add_argument("pdf")
    k.add_argument("model")
    a = ap.parse_args(argv)

    if a.cmd == "resolve":
        config = {"cv": CV, "site": SITE}.get(a.config) or yaml.safe_load(Path(a.config).read_text())
        model = resolve(config, load(a.data))
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(model, ensure_ascii=False, indent=1))
    else:
        limit = json.loads(Path(a.model).read_text()).get("max_pages")
        n = pdf_pages(a.pdf)
        if limit and n > limit:
            sys.exit(f"{a.pdf}: {n} pages, limit is {limit}. Trim the variant (max_bullets, sections).")
        print(f"{a.pdf}: {n} page(s)" + (f" (limit {limit})" if limit else ""))


if __name__ == "__main__":
    main()
