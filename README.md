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

## Layout

- `main.tex` — root document
- `chapters/` — one file per chapter (`\include`)
- `figures/` — final PNG/JPEG figures (sources live outside this repo or in local `figures/_raw/`, which is gitignored)

## License

Course slide figures were derived from EBI structural bioinformatics training materials and related workshops; retain appropriate attribution if you redistribute derived works.
