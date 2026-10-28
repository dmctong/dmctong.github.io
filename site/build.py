"""Render the site model (scripts/career.py resolve site) to a static page.

    site/build.py build/site.json build/site
Writes the plain document-style page (classic.py) as index.html, the designed
intro page to intro/ (with style.css, and headshot.jpg if present), and copies
the PDFs listed in `downloads` from the model's directory.
"""
import json
import re
import shutil
import sys
from html import escape
from pathlib import Path

import classic

HERE = Path(__file__).resolve().parent
HEADSHOT = HERE / "headshot.jpg"  # optional; initials are shown without it
SHOWN_BULLETS = 3  # the rest of an entry's bullets fold under "Show more"
TIMELINE = {"experience", "service", "education"}  # other entry sections are cards
CHIPS = {"skills"}  # "Label: a, b, c" items rendered as tag chips

# Contact pills: (pattern on the link, label shown, inline icon).
ICON = '<svg viewBox="0 0 24 24" aria-hidden="true">{}</svg>'
CONTACTS = [
    ("mailto:", "Email", '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>'),
    ("linkedin.com", "LinkedIn", '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 10v7M8 7v.01M12 17v-4a2 2 0 0 1 4 0v4M12 10v7"/>'),
    ("github.com", "GitHub", '<path d="M9 19c-4 1.5-4-2-6-2.5m12 5v-3.5a3 3 0 0 0-.9-2.4c3-.3 6-1.5 6-6.6a5 5 0 0 0-1.4-3.6 4.7 4.7 0 0 0-.1-3.5s-1.1-.3-3.6 1.4a12.4 12.4 0 0 0-6.5 0C6 1.6 4.9 1.9 4.9 1.9a4.7 4.7 0 0 0-.1 3.5A5 5 0 0 0 3.4 9c0 5.1 3 6.3 6 6.6a3 3 0 0 0-.9 2.4V22"/>'),
    ("orcid.org", "ORCID", '<circle cx="12" cy="12" r="9"/><path d="M9 10v6M9 7.5v.01M12.5 16v-6h1.5a3 3 0 0 1 0 6z"/>'),
    ("scholar.google", "Scholar", '<path d="m2 9 10-6 10 6-10 6z"/><path d="M6 11.5V16c2 2.5 10 2.5 12 0v-4.5"/>'),
]
PIN = '<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>'


def rich(runs):
    out = []
    for r in runs:
        h = escape(r["text"])
        if r.get("bold"):
            h = f"<strong>{h}</strong>"
        if r.get("italic"):
            h = f"<em>{h}</em>"
        if r.get("link"):
            h = f'<a href="{escape(r["link"])}">{h}</a>'
        out.append(h)
    return "".join(out)


def plain(runs):
    return "".join(r["text"] for r in runs)


def years(when):
    """'Feb. 2025 – present' -> '2025 – present'; 'June 2019' -> '2019'."""
    ys = re.findall(r"\d{4}|present", when)
    return " – ".join(dict.fromkeys(ys)) or when


def bullets(bs):
    if not bs:
        return ""
    items = [f"<li>{rich(b)}</li>" for b in bs]
    shown, rest = items[:SHOWN_BULLETS], items[SHOWN_BULLETS:]
    more = (f'<details><summary>Show {len(rest)} more</summary><ul>{"".join(rest)}</ul></details>'
            if rest else "")
    return f'<ul>{"".join(shown)}</ul>{more}'


def card(e):
    """An entry's first line is the title, the second the organization. The span
    shown on the timeline is the organization's when it has one (InsightRX
    2020 – present), with the current title's own dates beside the title."""
    (title, t_when), *rest = [(l["left"], l["right"]) for l in e["lines"]]
    org, o_when = rest[0] if rest else ([], "")
    span = years(o_when or t_when)
    role_when = f'<span class="when">{escape(t_when)}</span>' if o_when and t_when else ""
    desc = f'<p class="desc">{escape(e["description"])}</p>' if e["description"] else ""
    footer = f'<p class="prior">{rich(e["footer"])}</p>' if e.get("footer") else ""
    body = (f'<h3>{rich(title)}{role_when}</h3>'
            + (f'<p class="org">{rich(org)}</p>' if org else "")
            + desc + bullets(e["bullets"]) + footer)
    return span, body


def entries(s):
    if s["id"] in TIMELINE:
        items = []
        for e in s["entries"]:
            span, body = card(e)
            items.append(f'<li class="tl-item"><span class="tl-date">{escape(span)}</span>'
                         f'<span class="tl-dot"></span><div class="card">{body}</div></li>')
        return f'<ol class="timeline">{"".join(items)}</ol>'
    cards = []
    for e in s["entries"]:
        span, body = card(e)
        cards.append(f'<div class="card"><span class="tag">{escape(span)}</span>{body}</div>')
    return f'<div class="grid">{"".join(cards)}</div>'


def chips(item):
    label, *rest = item
    terms = plain(rest).split(", ")
    return (f'<div class="chip-row"><h3>{escape(plain([label]).rstrip(": "))}</h3>'
            f'<p class="chips">{"".join(f"<span>{escape(x)}</span>" for x in terms)}</p></div>')


def listing(s):
    intro = f'<p class="lead-sm">{rich(s["intro"])}</p>' if s["intro"] else ""
    note = f'<p class="note">{rich(s["note"])}</p>' if s["note"] else ""
    if s["id"] in CHIPS:
        return intro + "".join(chips(i) for i in s["items"]) + note
    tag = "ol reversed" if s["numbered"] else "ul"
    items = "".join(f"<li>{rich(i)}</li>" for i in s["items"])
    return f'{intro}<{tag} class="refs">{items}</{tag.split()[0]}>{note}'


def section(s):
    body = {"paragraph": lambda s: f'<p>{rich(s["text"])}</p>', "entries": entries, "list": listing}[s["kind"]](s)
    return (f'<section id="{s["id"]}" class="reveal" data-kind="{s["id"]}">'
            f'<h2>{escape(s["title"])}</h2>{body}</section>')


def published(d):
    return d.get("publish_as", d["file"])


def contact(c):
    link = next((r["link"] for r in c if r.get("link")), "")
    for pattern, label, icon in CONTACTS:
        if pattern in link:
            return f'<a class="pill" href="{escape(link)}" title="{escape(plain(c))}">{ICON.format(icon)}{label}</a>'
    if link:  # the site's own address; no need to link to the page you're on
        return ""
    return f'<span class="pill quiet">{ICON.format(PIN)}{escape(plain(c))}</span>'


def avatar(name):
    if HEADSHOT.exists():
        return f'<img class="avatar" src="headshot.jpg" alt="{escape(name)}">'
    initials = "".join(w[0] for w in name.split()[:2])
    return f'<div class="avatar mono" aria-hidden="true">{escape(initials)}</div>'


SCRIPT = """
<script>
document.documentElement.classList.add("js");
const io = new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
}), {rootMargin: "0px 0px -8% 0px"});
document.querySelectorAll(".reveal").forEach(el => io.observe(el));
const links = [...document.querySelectorAll("nav.float a")];
const spy = new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) links.forEach(a => a.classList.toggle("on", a.hash === "#" + e.target.id));
}), {rootMargin: "-45% 0px -50% 0px"});
document.querySelectorAll("main section").forEach(s => spy.observe(s));
</script>"""


def page(m):
    p = m["person"]
    summary = next((s for s in m["sections"] if s["id"] == "summary"), None)
    sections = [s for s in m["sections"] if s is not summary]
    cred = f'<span class="cred">, {escape(p["credentials"])}</span>' if p["credentials"] else ""
    contacts = "".join(contact(c) for c in p["contacts"])
    downloads = "".join(f'<a class="btn{" primary" if i == 0 else ""}" href="../{escape(published(d))}">{escape(d["label"])}</a>'
                        for i, d in enumerate(m["downloads"]))
    nav = "".join(f'<a href="#{s["id"]}">{escape(s["title"].split(" and ")[0].split(" & ")[0])}</a>'
                  for s in sections)
    lead = (f'<p class="lead">{escape(m["intro"])}</p>' if m.get("intro")
            else f'<p class="lead">{rich(summary["text"])}</p>' if summary else "")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(p["name"])}</title>
<meta name="description" content="{escape(p["headline"] or "")}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,600&display=swap">
<link rel="stylesheet" href="style.css">
</head>
<body>
<nav class="float" aria-label="Sections"><a class="home" href="#top">{escape("".join(w[0] for w in p["name"].split()[:2]))}</a>{nav}</nav>
<header id="top" class="hero">
<div class="hero-inner">
{avatar(p["name"])}
<div>
<h1>{escape(p["name"])}{cred}</h1>
<p class="headline">{escape(p["headline"] or "")}</p>
</div>
</div>
{lead}
<p class="contacts">{contacts}</p>
<p class="downloads">{downloads}<a class="btn" href="../">Plain résumé view</a></p>
</header>
<main>
{"".join(section(s) for s in sections)}
</main>
<footer>Updated {escape(m["generated"])}</footer>
{SCRIPT}
</body>
</html>
"""


def main(model_path, out_dir):
    model_path, out = Path(model_path), Path(out_dir)
    m = json.loads(model_path.read_text())
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(classic.page(m))
    shutil.copy(HERE / "classic.css", out / "classic.css")
    intro = out / "intro"
    intro.mkdir(exist_ok=True)
    (intro / "index.html").write_text(page(m))
    shutil.copy(HERE / "style.css", intro / "style.css")
    if HEADSHOT.exists():
        shutil.copy(HEADSHOT, intro / HEADSHOT.name)
    for d in m["downloads"]:
        src = model_path.parent / d["file"]
        if not src.exists():
            sys.exit(f"missing download {src}; build PDFs first")
        shutil.copy(src, out / published(d))


if __name__ == "__main__":
    main(*sys.argv[1:3])
