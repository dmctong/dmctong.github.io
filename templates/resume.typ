// Resume: one variant per run. Build with
//   typst compile --root . --input data=/build/<variant>.json templates/resume.typ out.pdf
#import "common.typ": *

#let model = json(sys.inputs.data)
#let p = model.person

#set document(title: p.name + " — Resume", author: p.name)
#set page(paper: "us-letter", margin: (x: 0.7in, top: 0.55in, bottom: 0.6in))
#show: base-styles.with(size: 10.5pt)

#header(p)
#for s in model.sections { section(s, gap: 0.75em, entry-gap: 0.75em) }
