// Shared rendering for the document model produced by scripts/career.py.
// Templates call `render(model, ...)` after setting page and text styles.

#let accent = rgb("#1f4e79")
#let rule = luma(170)

// Rich text: a list of runs {text, bold?, italic?, link?}.
#let rich(runs) = {
  for r in runs {
    let body = r.text
    if r.at("bold", default: false) { body = strong(body) }
    if r.at("italic", default: false) { body = emph(body) }
    if "link" in r { link(r.link, body) } else { body }
  }
}

#let header(p, contact-sep: [ #h(0.3em)|#h(0.3em) ]) = {
  set align(center)
  block(below: 0.55em, {
    text(size: 2.1em, p.name)
    if p.credentials != none { text(size: 1.3em)[, #p.credentials] }
  })
  if p.headline != none { block(below: 0.45em, text(size: 1.02em, p.headline)) }
  block(text(size: 0.92em, p.contacts.map(rich).join(contact-sep)))
}

#let section-title(title, gap) = {
  v(gap)
  block(sticky: true, below: 0.55em, {
    text(size: 1.25em, fill: accent, title)
    v(-0.75em)
    line(length: 100%, stroke: 0.5pt + rule)
  })
}

#let entry(e, gap) = block(above: gap, breakable: true, {
  for l in e.lines {
    block(above: 0.35em, below: 0.35em, sticky: true,
      grid(columns: (1fr, auto), column-gutter: 1em, rich(l.left), l.right))
  }
  if e.description != none { block(above: 0.6em, e.description) }
  if e.bullets.len() > 0 { list(..e.bullets.map(rich)) }
})

#let section(s, gap: 1em, entry-gap: 0.9em) = {
  section-title(s.title, gap)
  if s.kind == "paragraph" {
    rich(s.text)
  } else if s.kind == "entries" {
    for e in s.entries { entry(e, entry-gap) }
  } else if s.kind == "list" {
    if s.intro != none { block(below: 0.7em, rich(s.intro)) }
    if s.numbered {
      enum(reversed: true, ..s.items.map(rich))
    } else {
      list(..s.items.map(rich))
    }
    if s.note != none { block(above: 0.6em, rich(s.note)) }
  }
}

#let base-styles(doc, size: 10.5pt) = {
  set text(font: "Libertinus Serif", size: size, lang: "en")
  set par(leading: 0.52em, spacing: 0.7em)
  set list(indent: 0.8em, body-indent: 0.5em, spacing: 0.42em, marker: [•])
  set enum(indent: 0.2em, body-indent: 0.5em, spacing: 0.5em)
  show link: it => text(fill: accent, it)
  doc
}
