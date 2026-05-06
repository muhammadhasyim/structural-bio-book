# Structural Bioinformatics

Tufte-style LaTeX textbook on structural bioinformatics (theory-focused).

## Build

Requires a full TeX Live (or MacTeX) installation with `latexmk`, `biber`, and the `tufte-book` class.

```bash
latexmk -pdf main.tex
```

Clean auxiliary files:

```bash
latexmk -C main.tex
```

## Web edition (GitHub Pages)

The HTML site is a **Quarto** book using the vendored [Tufte Quarto](https://github.com/fredguth/tufte-quarto) extension (`_extensions/tufte/`). Canonical prose remains LaTeX (`main.tex`, `chapters/`); `website/quarto_gen.py` (run automatically via `pre-render` in `_quarto.yml`) converts each chapter with Pandoc into root-level `ch##_*.qmd` files next to `index.qmd`, then `quarto render` writes `_book/` with short URLs such as `ch01_foundations.html`.

**Local preview**

```bash
quarto render   # or: quarto preview
```

**CI** (`.github/workflows/pages.yml`) installs Quarto and Pandoc, runs `python3 website/quarto_gen.py` then `quarto render`, and pushes **`_book/`** to the **`gh-pages`** branch.

The older Pandoc chunk pipeline (`website/build.sh` → `website/dist/`) is retained only for comparison; it is no longer what Pages deploys.

**One-time setup** ([Pages settings](https://github.com/muhammadhasyim/structural-bio-book/settings/pages)):

1. Under **Build and deployment**, set **Source** to **Deploy from a branch** (not “GitHub Actions”).
2. Choose **Branch** `gh-pages`, folder **`/ (root)`**, then Save.
3. After the first successful workflow run, the site appears at your Pages URL (often `https://muhammadhasyim.github.io/structural-bio-book/`).

If you prefer the **GitHub Actions** deployment API instead, you can switch the workflow back to `actions/deploy-pages` and set Pages **Source** to **GitHub Actions**; that path returns **404** until that source is enabled in the UI.

**Note:** The vendored Tufte extension had its contributed **PDF** format removed so `quarto render` on CI does not require a TeX installation. The print book is still built with `latexmk` as above.

## Layout

- `main.tex` — root document
- `chapters/` — one file per chapter (`\include`)
- `_quarto.yml` — Quarto Tufte book (GitHub Pages output under `_book/`)
- `website/quarto_gen.py` — generates `ch##_*.qmd` from the LaTeX sources before each render (gitignored)
- `website/html_fig_img_alt.py` — post-render step (see `_quarto.yml`): copies figure captions onto `<img alt="…">` for margin-caption HTML
- `figures/` — final PNG/JPEG figures (sources live outside this repo or in local `figures/_raw/`, which is gitignored)

## License

Course slide figures were derived from EBI structural bioinformatics training materials and related workshops; retain appropriate attribution if you redistribute derived works.
