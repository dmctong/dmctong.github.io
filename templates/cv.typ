// Full academic CV: every section, full author lists, numbered publications.
//   typst compile --root . --input data=/build/cv.json templates/cv.typ out.pdf
#import "common.typ": *

#let model = json(sys.inputs.data)
#let p = model.person

#set document(title: p.name + " — Curriculum Vitae", author: p.name)
#set page(
  paper: "us-letter",
  margin: (x: 0.85in, top: 0.75in, bottom: 0.8in),
  footer: context {
    set text(size: 8.5pt, fill: luma(110))
    grid(columns: (1fr, auto),
      [#p.name — Curriculum Vitae — updated #model.generated],
      counter(page).display("1 of 1", both: true))
  },
)
#show: base-styles.with(size: 10.5pt)

#header(p)
#for s in model.sections { section(s, gap: 1.1em, entry-gap: 0.9em) }
