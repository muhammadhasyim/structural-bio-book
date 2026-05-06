#!/usr/bin/env python3
"""
Post-render: copy ``<figcaption>`` text onto ``<img>`` as ``alt`` when missing or placeholder.

Quarto with ``fig-cap-location: margin`` often emits ``<img>`` without a useful ``alt`` while
putting the caption in ``<figcaption class="margin-caption">``. Browsers and assistive tech
then surface a bare word like "image".
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

    return _FIGURE_BLOCK.sub(repl, html)


def main() -> None:
    out_dir = Path(os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "_book")).resolve()
    if not out_dir.is_dir():
        print(f"html_fig_img_alt: skip (not a directory): {out_dir}", file=sys.stderr)
        return
    n_files = 0
    for path in sorted(out_dir.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        new_text = patch_html_document(text)
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
    out = patch_html_document(sample)
    assert 'alt="Myoglobin side view."' in out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        _self_test()
    else:
        main()
