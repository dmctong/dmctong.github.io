// The 1200×627 link-preview card (og:image) for the site, from the site model.
#let m = json(sys.inputs.data)
#let p = m.person
#let (role, ..focus) = p.headline.split(" | ")
#let accent = rgb("#2456d6")
#let accent2 = rgb("#0f9d8a")
#let muted = rgb("#5d636e")

#set page(width: 1200pt, height: 627pt, margin: 0pt, fill: rgb("#f7f7f4"))
#set text(font: "Libertinus Serif", fill: rgb("#16181d"), lang: "en")

#place(top + left, dx: -200pt, dy: -150pt,
  circle(radius: 380pt, fill: gradient.radial(accent.transparentize(84%), accent.transparentize(100%))))
#place(bottom + right, dx: 160pt, dy: 220pt,
  circle(radius: 420pt, fill: gradient.radial(accent2.transparentize(84%), accent2.transparentize(100%))))
#place(bottom + left, rect(width: 100%, height: 10pt, fill: gradient.linear(accent, accent2)))

#place(horizon + left, dx: 90pt, grid(
  columns: (340pt, 1fr), column-gutter: 70pt, align: horizon,
  box(width: 340pt, height: 340pt, radius: 50%, clip: true, stroke: 6pt + white,
    image("/site/headshot.jpg", width: 100%, height: 100%, fit: "cover")),
  block(width: 610pt)[
    #text(size: 76pt, weight: "bold")[#p.name]
    #if p.credentials != none [#text(size: 40pt, fill: muted)[, #p.credentials]]
    #v(4pt)
    #text(size: 34pt)[#role]
    #v(-6pt)
    #text(size: 30pt, fill: accent)[#focus.join(" · ")]
    #v(26pt)
    #text(size: 26pt, fill: muted)[#p.contacts.find(c => c.at(0).at("link", default: "").contains("github.io")).at(0).text]
  ],
))
