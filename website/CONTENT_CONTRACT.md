# LaTeX → HTML content contract (web book)

For each construct, fix **structure in the pipeline** (flatten / Lua / template) before tuning **CSS** in `site.css`. Vendored `tufte.css` is not edited.

| Construct | Intended HTML (rough) | Owner (preprocess / filter / CSS) | Status |
|-----------|----------------------|-----------------------------------|--------|
| `\chapter` | Chunk + `h1` inside `article > section` | Pandoc `chunkedhtml` + `template-chunked.html` | Done |
| `\newthought` | `span.newthought` | `filters/newthought.lua` + flatten `<<NT>>` marker | Done |
| `\footnote` / sidenotes | Tufte checkbox sidenote pattern | `filters/pandoc-sidenote.lua` + `replace_sidenote` in flatten | Done |
| `figure*` | `figure.fullwidth` + caption | `flatten_for_web.py` (JSON labels) + `filters/fullwidth_figures.lua` | Done |
| `marginfigure` + `\caption` | `div.marginfigure` + image + `blockquote` (caption body under image) | `flatten_for_web.py` (`marginfigure_promote_captions_inner`) | Done |
| `algorithm` | `pre` / code block with algorithm class | `flatten_for_web.py` (verbatim wrap) + `filters/algorithm_codeblock.lua` | Done (when present) |

**Rule:** If the browser looks wrong, classify as *content loss*, *wrong structure*, or *styling only* — only the last belongs as the first fix in `site.css`.
