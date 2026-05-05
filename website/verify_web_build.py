#!/usr/bin/env python3
"""Light post-build checks for the chunked HTML site (regression net)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dist",
        type=Path,
        required=True,
        help="Path to website/dist after build.sh",
    )
    ap.add_argument(
        "--expect-chapter-html",
        type=int,
        default=12,
        help="Expected number of *-ch:*.html chapter files (default: 12).",
    )
    args = ap.parse_args()
    dist = args.dist.resolve()
    errors: list[str] = []

    index = dist / "index.html"
    sitemap = dist / "sitemap.json"
    if not index.is_file():
        errors.append(f"missing {index}")
    if not sitemap.is_file():
        errors.append(f"missing {sitemap}")

    if index.is_file():
        text = index.read_text(encoding="utf-8")
        if '<nav id="toc"' not in text:
            errors.append("index.html: missing injected <nav id=\"toc\" ...>")
        if "<article>" not in text:
            errors.append("index.html: missing <article>")

    chapters = sorted(dist.glob("*-ch:*.html"))
    if len(chapters) != args.expect_chapter_html:
        errors.append(
            f"expected {args.expect_chapter_html} *-ch:*.html files, found {len(chapters)}",
        )

    for path in chapters:
        t = path.read_text(encoding="utf-8")
        if "<article>" not in t:
            errors.append(f"{path.name}: missing <article>")
        if "<section>" not in t:
            errors.append(f"{path.name}: missing <section>")

    if errors:
        for e in errors:
            print(f"verify_web_build: {e}", file=sys.stderr)
        return 1
    print(
        f"verify_web_build: OK ({len(chapters)} chapter HTML, index + sitemap present)",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
