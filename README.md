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

CI builds the static site with Pandoc (`website/build.sh`) and pushes `website/dist` to the **`gh-pages`** branch (`.github/workflows/pages.yml`).

**One-time setup** ([Pages settings](https://github.com/muhammadhasyim/structural-bio-book/settings/pages)):

1. Under **Build and deployment**, set **Source** to **Deploy from a branch** (not “GitHub Actions”).
2. Choose **Branch** `gh-pages`, folder **`/ (root)`**, then Save.
3. After the first successful workflow run, the site appears at your Pages URL (often `https://muhammadhasyim.github.io/structural-bio-book/`).

If you prefer the **GitHub Actions** deployment API instead, you can switch the workflow back to `actions/deploy-pages` and set Pages **Source** to **GitHub Actions**; that path returns **404** until that source is enabled in the UI.

## Layout

- `main.tex` — root document
- `chapters/` — one file per chapter (`\include`)
- `figures/` — final PNG/JPEG figures (sources live outside this repo or in local `figures/_raw/`, which is gitignored)

## License

Course slide figures were derived from EBI structural bioinformatics training materials and related workshops; retain appropriate attribution if you redistribute derived works.
