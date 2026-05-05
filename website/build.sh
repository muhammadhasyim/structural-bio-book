#!/usr/bin/env bash
# Build static site for GitHub Pages (Pandoc + Tufte CSS).
#
# Pipeline (single source of truth):
#   1. flatten_for_web.py  -> build/merged.tex + fullwidth-figures.json
#   2. Vendor Tufte CSS/fonts into dist/ (zip checksum pinned; see tufte-css-gh-pages.zip.sha256)
#   3. pandoc chunkedhtml  -> zip -> unzip into dist/
#   4. inject_index_toc.py -> index.html chapter list from sitemap.json
#   5. verify_web_build.py -> quick structural checks
#
# Lua filter order (--lua-filter is applied in list order; later filters see AST from earlier ones):
#   - newthought.lua: turn <<NT>>... markers from flatten into span.newthought before other
#     inline transforms that might split paragraphs.
#   - pandoc-sidenote.lua: footnote -> Tufte sidenote markup (needs stable paras; run before
#     blocks that rewrite figure/div structure broadly).
#   - algorithm_codeblock.lua: tag verbatim blocks that came from algorithm envs (marker
#     WEB-ALGORITHM-BEGIN) for CSS; independent of figures.
#   - fullwidth_figures.lua: promote figure* / labels from PANDOC_FULLWIDTH_JSON to
#     figure.fullwidth; run last so it sees the final Figure/Div structure.
#
set -euo pipefail

WEB_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$WEB_DIR/.." && pwd)"
BUILD="$WEB_DIR/build"
DIST="$WEB_DIR/dist"
ZIP_TMP="$BUILD/chunked.zip"
TUFE_ZIP="$BUILD/tufte-css-gh-pages.zip"
TUFE_SHA_FILE="$WEB_DIR/tufte-css-gh-pages.zip.sha256"

rm -rf "$DIST" "$BUILD"
mkdir -p "$BUILD" "$DIST"

python3 "$WEB_DIR/flatten_for_web.py" \
  --book-root "$ROOT" \
  --output "$BUILD/merged.tex" \
  --fullwidth-json "$BUILD/fullwidth-figures.json"

curl -fsSL "https://codeload.github.com/edwardtufte/tufte-css/zip/refs/heads/gh-pages" -o "$TUFE_ZIP"
EXPECTED_TUFE_SHA256="$(tr -d ' \n\t' < "$TUFE_SHA_FILE")"
ACTUAL_TUFE_SHA256="$(openssl dgst -sha256 "$TUFE_ZIP" | awk '{print $NF}')"
if [[ "$ACTUAL_TUFE_SHA256" != "$EXPECTED_TUFE_SHA256" ]]; then
  echo "error: Tufte CSS zip SHA-256 mismatch (expected $EXPECTED_TUFE_SHA256, got $ACTUAL_TUFE_SHA256)." >&2
  echo "Update tufte-css-gh-pages.zip.sha256 after verifying upstream changes." >&2
  exit 1
fi
unzip -qo "$TUFE_ZIP" -d "$BUILD"
cp "$BUILD/tufte-css-gh-pages/tufte.css" "$DIST/"
cp -R "$BUILD/tufte-css-gh-pages/et-book" "$DIST/"
cp "$WEB_DIR/site.css" "$DIST/"
cp -R "$ROOT/figures" "$DIST/"

export PANDOC_FULLWIDTH_JSON="$BUILD/fullwidth-figures.json"
pandoc "$BUILD/merged.tex" \
  --from=latex \
  --to=chunkedhtml \
  --split-level=1 \
  --toc \
  --toc-depth=2 \
  --standalone \
  --template="$WEB_DIR/template-chunked.html" \
  --lua-filter="$WEB_DIR/filters/newthought.lua" \
  --lua-filter="$WEB_DIR/filters/pandoc-sidenote.lua" \
  --lua-filter="$WEB_DIR/filters/algorithm_codeblock.lua" \
  --lua-filter="$WEB_DIR/filters/fullwidth_figures.lua" \
  --citeproc \
  --bibliography="$ROOT/references.bib" \
  --resource-path="$ROOT" \
  --metadata=title:"Structural Bioinformatics" \
  --metadata=author:"" \
  --metadata=base-url:"https://muhammadhasyim.github.io/structural-bio-book/" \
  --mathjax \
  --css=tufte.css \
  --css=site.css \
  -o "$ZIP_TMP"

unzip -qo "$ZIP_TMP" -d "$DIST"
rm -f "$ZIP_TMP"

python3 "$WEB_DIR/inject_index_toc.py" --dist "$DIST"
python3 "$WEB_DIR/verify_web_build.py" --dist "$DIST"

echo "Built site in $DIST (open $DIST/index.html)"
