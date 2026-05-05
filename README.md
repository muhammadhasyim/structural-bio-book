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

CI builds the static site with Pandoc (see `website/build.sh`) and deploys via `.github/workflows/pages.yml`.

If the deploy job fails with **HttpError: Not Found** or **Failed to create deployment (404)**, enable Pages for this repository:

1. Open **Settings → Pages**: `https://github.com/muhammadhasyim/structural-bio-book/settings/pages`
2. Under **Build and deployment**, set **Source** to **GitHub Actions** (not “Deploy from a branch”).
3. Re-run the failed workflow (**Actions** → workflow run → **Re-run all jobs**) or push a small commit.

Until Source is **GitHub Actions**, the Pages deployment API returns 404 and `deploy-pages` cannot create a deployment.

## Layout

- `main.tex` — root document
- `chapters/` — one file per chapter (`\include`)
- `figures/` — final PNG/JPEG figures (sources live outside this repo or in local `figures/_raw/`, which is gitignored)

## License

Course slide figures were derived from EBI structural bioinformatics training materials and related workshops; retain appropriate attribution if you redistribute derived works.
