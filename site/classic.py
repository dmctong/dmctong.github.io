"""The plain, document-style page: the site's main page.

site/build.py writes it from the same model, alongside the designed intro page
at intro/ that it links to.
"""
from html import escape


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


def entries(s):
    parts = []
    for e in s["entries"]:
        lines = "".join(
            f'<div class="line"><span>{rich(l["left"])}</span>'
            f'<span class="when">{escape(l["right"])}</span></div>' for l in e["lines"])
        desc = f'<p>{escape(e["description"])}</p>' if e["description"] else ""
        bullets = "".join(f"<li>{rich(b)}</li>" for b in e["bullets"])
        footer = f'<p class="prior">{rich(e["footer"])}</p>' if e.get("footer") else ""
        parts.append(f'<article class="entry">{lines}{desc}{"<ul>" + bullets + "</ul>" if bullets else ""}{footer}</article>')
    return "".join(parts)


def listing(s):
    tag = "ol reversed" if s["numbered"] else "ul"
    items = "".join(f"<li>{rich(i)}</li>" for i in s["items"])
    intro = f'<p>{rich(s["intro"])}</p>' if s["intro"] else ""
    note = f'<p class="note">{rich(s["note"])}</p>' if s["note"] else ""
    return f'{intro}<{tag} class="refs">{items}</{tag.split()[0]}>{note}'


def section(s):
    body = {"paragraph": lambda s: f'<p>{rich(s["text"])}</p>', "entries": entries, "list": listing}[s["kind"]](s)
    return f'<section id="{s["id"]}"><h2>{escape(s["title"])}</h2>{body}</section>'


def published(d):
    return d.get("publish_as", d["file"])


def page(m):
    p = m["person"]
    name = escape(p["name"]) + (f', <span class="cred">{escape(p["credentials"])}</span>' if p["credentials"] else "")
    contacts = " · ".join(rich(c) for c in p["contacts"])
    downloads = " ".join(f'<a class="btn" href="{escape(published(d))}">{escape(d["label"])}</a>'
                         for d in m["downloads"])
    nav = " ".join(f'<a href="#{s["id"]}">{escape(s["title"])}</a>' for s in m["sections"])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(p["name"])}</title>
<meta name="description" content="{escape(p["headline"] or "")}">
<link rel="stylesheet" href="classic.css">
</head>
<body>
<header>
<h1>{name}</h1>
<p class="headline">{escape(p["headline"] or "")}</p>
<p class="contacts">{contacts}</p>
<p class="downloads">{downloads}</p>
<nav>{nav} <a href="intro/">Interactive version</a></nav>
</header>
<main>
{"".join(section(s) for s in m["sections"])}
</main>
<footer>Updated {escape(m["generated"])}</footer>
</body>
</html>
"""
