#!/usr/bin/env python3
"""
Post-render HTML fixes for Quarto ``_book`` output.

1. Copy ``<figcaption>`` text onto ``<img>`` as ``alt`` when missing or placeholder.

   Quarto with ``fig-cap-location: margin`` often emits ``<img>`` without a useful ``alt`` while
   putting the caption in ``<figcaption class="margin-caption">``. Browsers and assistive tech
   then surface a bare word like "image".

2. Unwrap ``\\[ ... \\]`` around AMS display envs (``equation``, ``align``, ``aligned``, …) in
   ``span.math.display``. Nesting breaks MathJax AMS numbering and ``\\eqref`` / ``\\ref`` (often "???").

3. Some Quarto/Pandoc versions emit ``\\[\\label{eq:...} ... \\]`` instead of ``\\begin{equation}``.
   Those spans get rewritten to ``\\begin{equation}\\label{...} ... \\end{equation}``.
"""
from __future__ import annotations

import html as html_module
import os
import re
import sys
from pathlib import Path

_FIGURE_BLOCK = re.compile(
    r"<figure\b[^>]*\bclass=\"[^\"]*\bfigure\b[^\"]*\"[^>]*>(.*?)</figure>",
    re.IGNORECASE | re.DOTALL,
)
_CAPTION = re.compile(
    r"<figcaption\b[^>]*>(.*?)</figcaption>",
    re.IGNORECASE | re.DOTALL,
)
_TAG = re.compile(r"<[^>]+>")

# Quarto wraps display math as ``\[ ... \]``.  AMS display environments such as
# ``equation`` and ``align`` already open display mode; nesting breaks tagging,
# equation numbers, and ``\eqref`` (often shown as ``???`` in the browser).
_AMS_NESTABLE_ENV = (
    r"equation\*?|align\*?|aligned|gather\*?|multline\*?|flalign\*?|eqnarray\*?"
)
_DISPLAY_MATH_SPAN_RE = re.compile(
    r'<span\s+class="math display">(.*?)</span>',
    re.DOTALL | re.IGNORECASE,
)
_NESTED_AMS_ENV_OPEN_RE = re.compile(
    r"\\\[\s*(?P<begin>\\begin\{(" + _AMS_NESTABLE_ENV + r")\})"
)
_NESTED_AMS_ENV_CLOSE_RE = re.compile(
    r"(?P<end>\\end\{(" + _AMS_NESTABLE_ENV + r")\})\s*\\\]"
)


def unwrap_nested_amsmath_display_delimiters(html: str) -> str:
    """Strip a leading ``\\[`` / trailing ``\\]`` pair when they wrap AMS display envs (equation, align, …)."""

    html = _NESTED_AMS_ENV_OPEN_RE.sub(lambda m: m.group("begin"), html)
    html = _NESTED_AMS_ENV_CLOSE_RE.sub(lambda m: m.group("end"), html)
    return html


def convert_label_only_display_spans(html: str) -> str:
    """
    Pandoc sometimes outputs ``\\[\\label{eq:...} ... \\]`` (no ``equation`` env). MathJax then
    fails to tag/number, so ``\\ref`` becomes ???. Wrap as ``\\begin{equation}...\\end{equation}``.
    """

    def repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        t = inner.strip()
        if len(t) < 4 or not t.startswith(r"\[") or not t.endswith(r"\]"):
            return m.group(0)
        body = t[2:-2].strip()
        if body.startswith(r"\label{") and r"\begin{" not in body:
            fixed = r"\begin{equation}" + body + r"\end{equation}"
            return '<span class="math display">' + fixed + "</span>"
        return m.group(0)

    return _DISPLAY_MATH_SPAN_RE.sub(repl, html)


def patch_math_for_github_pages(html: str) -> str:
    """Apply all HTML math normalizations (order matters)."""
    html = unwrap_nested_amsmath_display_delimiters(html)
    html = convert_label_only_display_spans(html)
    return html


def _strip_tags(html: str) -> str:
    return _TAG.sub("", html)


def _attr_escape(plain: str) -> str:
    t = html_module.unescape(_strip_tags(plain)).strip()
    return t.replace("&", "&amp;").replace('"', "&quot;").replace("\n", " ")


def _needs_alt_replacement(alt_inner: str | None) -> bool:
    if alt_inner is None:
        return True
    s = alt_inner.strip()
    return s == "" or s.lower() == "image"


def _patch_img_tag(img_tag: str, caption_plain: str) -> str:
    esc = _attr_escape(caption_plain)
    if not esc:
        return img_tag
    m = re.search(r'\balt\s*=\s*"([^"]*)"', img_tag, flags=re.IGNORECASE)
    if m and not _needs_alt_replacement(m.group(1)):
        return img_tag
    if m:
        return img_tag[: m.start()] + f'alt="{esc}"' + img_tag[m.end() :]
    if img_tag.lower().startswith("<img "):
        return '<img alt="' + esc + '" ' + img_tag[5:]
    return img_tag


def patch_figure_html(fragment: str) -> str:
    cap_m = _CAPTION.search(fragment)
    if not cap_m:
        return fragment
    caption_html = cap_m.group(1)

    def img_repl(im: re.Match[str]) -> str:
        return _patch_img_tag(im.group(0), caption_html)

    return re.sub(r"<img\b[^>]*>", img_repl, fragment, count=1, flags=re.IGNORECASE)


def patch_html_document(html: str) -> str:
    def repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        patched_inner = patch_figure_html(inner)
        return m.group(0).replace(inner, patched_inner, 1)

    html = _FIGURE_BLOCK.sub(repl, html)
    return html


def main() -> None:
    out_dir = Path(os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "_book")).resolve()
    if not out_dir.is_dir():
        print(f"html_fig_img_alt: skip (not a directory): {out_dir}", file=sys.stderr)
        return
    n_files = 0
    for path in sorted(out_dir.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        new_text = patch_html_document(patch_math_for_github_pages(text))
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            n_files += 1
    if os.environ.get("QUARTO_PROJECT_SCRIPT_PROGRESS") == "1":
        print(f"html_fig_img_alt: patched {n_files} HTML files under {out_dir}", file=sys.stderr)


def _self_test() -> None:
    sample = """<figure class="figure page-columns page-full">
<p><img src="figures/x.png" class="img-fluid figure-img"></p>
<figcaption class="margin-caption">Myoglobin side view.</figcaption>
</figure>"""
    out = patch_html_document(patch_math_for_github_pages(sample))
    assert 'alt="Myoglobin side view."' in out

    eq = '<span class="math display">\\[\\begin{equation}x\\end{equation}\\]</span>'
    out_eq = patch_math_for_github_pages(eq)
    assert "\\[" not in out_eq
    assert "\\begin{equation}x\\end{equation}" in out_eq

    lab = (
        '<span class="math display">\\[\\label{eq:z} Z = 1\\]</span>'
    )
    out_lab = patch_math_for_github_pages(lab)
    assert "\\[" not in out_lab
    assert "\\begin{equation}\\label{eq:z} Z = 1\\end{equation}" in out_lab

    al = '<span class="math display">\\[\\begin{aligned} a \\\\ b \\end{aligned}\\]</span>'
    out_al = patch_math_for_github_pages(al)
    assert "\\[" not in out_al
    assert "\\begin{aligned}" in out_al


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        _self_test()
    else:
        main()
