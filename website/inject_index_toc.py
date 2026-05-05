#!/usr/bin/env python3
"""Inject a chapter list into chunkedhtml index.html (Pandoc leaves it empty)."""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path


def walk_chapters(node: dict, out: list[tuple[str, str]]) -> None:
    sec = node.get("section") or {}
    if sec.get("level") == "1":
        raw_path = sec.get("path") or ""
        title = sec.get("title") or ""
        path = raw_path.split("#", 1)[0]
        if path.endswith(".html"):
            out.append((title, path))
    for child in node.get("subsections") or []:
        walk_chapters(child, out)


def part_link_from_zero(dist: Path) -> tuple[str, str] | None:
    zeros = sorted(dist.glob("0-*.html"))
    if not zeros:
        return None
    p = zeros[0]
    text = p.read_text(encoding="utf-8")
    m = re.search(r"<strong>([^<]+)</strong>", text)
    title = m.group(1).strip() if m else p.stem
    return title, p.name


def build_toc_entries(dist: Path, sitemap: dict) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    z = part_link_from_zero(dist)
    if z:
        entries.append(z)
    for sub in sitemap.get("subsections") or []:
        walk_chapters(sub, entries)
    seen: set[str] = set()
    uniq: list[tuple[str, str]] = []
    for title, href in entries:
        if href in seen:
            continue
        seen.add(href)
        uniq.append((title, href))
    return uniq


def inject_body(html: str, inner: str) -> str:
    return re.sub(r"<body>\s*", "<body>\n" + inner + "\n", html, count=1, flags=re.MULTILINE)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", type=Path, required=True)
    args = ap.parse_args()
    dist = args.dist.resolve()
    index = dist / "index.html"
    sm_path = dist / "sitemap.json"
    if not index.is_file():
        raise SystemExit(f"missing {index}")
    if not sm_path.is_file():
        raise SystemExit(f"missing {sm_path}")

    sitemap = json.loads(sm_path.read_text(encoding="utf-8"))
    root = sitemap.get("section") or {}
    book_title = root.get("title") or "Book"

    toc = build_toc_entries(dist, sitemap)
    lines = [
        "<article>",
        "<section>",
        f'<h1 class="title" id="book-title">{html.escape(book_title)}</h1>',
        "<p>Web edition built with Pandoc and Tufte CSS.</p>",
        '<nav id="toc" aria-label="Table of contents">',
        "<h2>Contents</h2>",
        "<ol>",
    ]
    for title, href in toc:
        lines.append(
            f'<li><a href="{html.escape(href)}">{html.escape(title)}</a></li>'
        )
    lines.extend(["</ol>", "</nav>", "</section>", "</article>"])
    block = "\n".join(lines)

    html_text = index.read_text(encoding="utf-8")
    index.write_text(inject_body(html_text, block), encoding="utf-8")


if __name__ == "__main__":
    main()
