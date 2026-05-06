#!/usr/bin/env python3
"""Generate Quarto chapter sources from canonical LaTeX (per-chapter Pandoc)."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from flatten_for_web import (
    iter_chapter_stems_with_parts,
    read_tex,
    transform_chapter_body,
)

CHAPTER_TITLE_RE = re.compile(r"^\\chapter(?:\[[^\]]*\])?\{([^}]*)\}", re.MULTILINE)
LEADING_LABEL_RE = re.compile(r"^\\label\{[^}]+\}\s*", re.MULTILINE)


def extract_chapter_title(tex: str) -> tuple[str | None, str]:
    m = CHAPTER_TITLE_RE.search(tex)
    if not m:
        return None, tex
    title = m.group(1).strip()
    body = tex[: m.start()] + tex[m.end() :]
    body = body.lstrip()
    body = LEADING_LABEL_RE.sub("", body, count=1)
    return title, body


def stem_to_out_name(include_stem: str) -> str:
    """``chapters/ch01_foundations`` -> ``ch01_foundations.qmd``."""
    return Path(include_stem).name + ".qmd"


def human_title_from_stem(include_stem: str) -> str:
    base = Path(include_stem).name
    if base.startswith("ch") and len(base) > 2 and base[2].isdigit():
        rest = base.split("_", 1)[-1] if "_" in base else base
        return rest.replace("_", " ").title()
    return base.replace("_", " ").title()


def wrap_latex_document(body: str) -> str:
    return (
        "\\documentclass{article}\n"
        "\\input{website/quarto_pandoc_stub.tex}\n"
        "\\begin{document}\n"
        f"{body}\n"
        "\\end{document}\n"
    )


def run_pandoc_latex_to_markdown(
    latex_full: str,
    *,
    book_root: Path,
    bib: Path | None,
    id_prefix: str,
) -> str:
    cmd = [
        "pandoc",
        "-f",
        "latex",
        "-t",
        "markdown",
        "--wrap=none",
        f"--resource-path={book_root}",
        f"--id-prefix={id_prefix}",
    ]
    if bib is not None and bib.is_file():
        cmd.append(f"--bibliography={bib}")
    proc = subprocess.run(
        cmd,
        input=latex_full,
        capture_output=True,
        text=True,
        cwd=book_root,
        check=False,
    )
    if proc.returncode != 0:
        msg = proc.stderr or proc.stdout or "pandoc failed"
        raise RuntimeError(msg)
    return proc.stdout.lstrip("\n")


# Generated chapter .qmd files live next to ``index.qmd`` (book project root); figures stay in
# repo-root ``figures/`` (same relative path from those .qmd files).
FIGURES_REL_FROM_CHAPTER_QMD = "figures/"


def adjust_markdown_paths_for_generated_chapter(md: str) -> str:
    """Rewrite Pandoc ``figures/`` image paths for chapter .qmd at the book project root."""
    return md.replace("](figures/", f"]({FIGURES_REL_FROM_CHAPTER_QMD}")


MARGINFIG_BLOCK = re.compile(r"^:::\s*marginfigure\s*\n(.*?)^:::\s*$", re.MULTILINE | re.DOTALL)
IMG_LINE_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)(\{[^}]*\})?\s*$")


def _blockquote_caption(block: str) -> tuple[str, str]:
    """Return (caption_text, remainder) from leading markdown blockquotes."""
    lines = block.splitlines()
    cap_lines: list[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("> "):
            cap_lines.append(ln[2:])
            i += 1
            continue
        if ln.startswith(">"):
            cap_lines.append(ln[1:].lstrip())
            i += 1
            continue
        if not ln.strip():
            i += 1
            continue
        break
    caption = " ".join(cap_lines).strip()
    rest = "\n".join(lines[i:]).lstrip()
    return caption, rest


def rewrite_marginfigure_blocks(md: str) -> str:
    r"""
    Turn Pandoc ``::: marginfigure`` (from LaTeX ``marginfigure``) into Quarto margin layout.

    Merges promoted ``\caption`` text (Pandoc ``>`` quote) into the image alt text so we do not
    show the default ``image`` placeholder caption, and uses ``::: {.column-margin}`` so figures
    sit in the margin per Quarto article layout.
    """

    def repl(m: re.Match[str]) -> str:
        inner = m.group(1).rstrip()
        parts = inner.split("\n", 1)
        first = parts[0].strip()
        tail = parts[1] if len(parts) > 1 else ""
        im = IMG_LINE_RE.match(first)
        if not im:
            return m.group(0)
        alt, path, attrs = im.group(1), im.group(2), im.group(3) or ""
        caption, _rest = _blockquote_caption(tail.strip("\n")) if tail.strip() else ("", "")
        if alt.strip().lower() == "image" or alt == "":
            alt = caption if caption else ""
        line = f"![{alt}]({path}){attrs}".rstrip()
        return f"::: {{.column-margin}}\n{line}\n:::\n"

    return MARGINFIG_BLOCK.sub(repl, md)


def rewrite_pandoc_equation_refs(md: str) -> str:
    r"""
    Pandoc writes equation references as markdown links, e.g.
    ``[\[eq:foo\]\](#eq:foo){reference-type="eqref" reference="eq:foo"}``,
    which never reach MathJax. Rewrite to inline math ``$\\eqref{eq:foo}$`` / ``$\\ref{eq:foo}$``.
    """

    def repl_eqref(m: re.Match[str]) -> str:
        gid = m.group(1)
        return f"$\\eqref{{{gid}}}$"

    def repl_ref(m: re.Match[str]) -> str:
        gid = m.group(1)
        return f"$\\ref{{{gid}}}$"

    md = re.sub(
        r'\[\\\[(eq:[^\]]+)\\\]\]\(#[^)]+\)\{'
        r'(?:[^}]*reference-type="eqref"[^}]*reference="\1"|'
        r'[^}]*reference="\1"[^}]*reference-type="eqref")'
        r'[^}]*\}',
        repl_eqref,
        md,
    )
    md = re.sub(
        r'\[\\\[(eq:[^\]]+)\\\]\]\(#[^)]+\)\{'
        r'(?:[^}]*reference-type="ref"[^}]*reference="\1"|'
        r'[^}]*reference="\1"[^}]*reference-type="ref")'
        r'[^}]*\}',
        repl_ref,
        md,
    )
    return md


def postprocess_chapter_markdown(md: str) -> str:
    md = adjust_markdown_paths_for_generated_chapter(md)
    md = rewrite_marginfigure_blocks(md)
    md = rewrite_pandoc_equation_refs(md)
    return md


def write_qmd(path: Path, title: str, markdown_body: str) -> None:
    header = "---\n" + f"title: {json.dumps(title, ensure_ascii=False)}\n" + "---\n\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + markdown_body.rstrip() + "\n", encoding="utf-8")


def write_generated_manifest(
    path: Path,
    *,
    parts: list[tuple[str | None, list[str]]],
) -> None:
    """JSON manifest for debugging / tooling (not required by Quarto)."""
    payload = {
        "parts": [
            {"part": p, "chapters": [stem_to_out_name(s) for s in stems]} for p, stems in parts
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def group_by_part(
    items: list[tuple[str | None, str]],
) -> list[tuple[str | None, list[str]]]:
    if not items:
        return []
    out: list[tuple[str | None, list[str]]] = []
    current_part = items[0][0]
    current_stems: list[str] = []
    for part, stem in items:
        if part != current_part and current_stems:
            out.append((current_part, current_stems))
            current_stems = []
        current_part = part
        current_stems.append(stem)
    if current_stems:
        out.append((current_part, current_stems))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--book-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root containing main.tex (default: parent of website/).",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Directory for generated chapter .qmd files (default: <book-root>, same as index.qmd).",
    )
    ap.add_argument(
        "--keep-tikz-source",
        action="store_true",
        help="Keep TikZ source in verbatim after the omission note (large output).",
    )
    args = ap.parse_args()
    book_root: Path = args.book_root.resolve()
    out_dir = args.out_dir.resolve() if args.out_dir is not None else book_root
    bib_path = book_root / "references.bib"
    bib_arg: Path | None = bib_path if bib_path.is_file() else None
    if bib_arg is None:
        print(f"quarto_gen: warning: missing {bib_path} (citations may not convert)", file=sys.stderr)

    items = iter_chapter_stems_with_parts(book_root)
    parts = group_by_part(items)

    for _part, stem in items:
        raw = read_tex(book_root, stem)
        title, body_wo_chapter = extract_chapter_title(raw)
        if not title:
            title = human_title_from_stem(stem)
        body = transform_chapter_body(body_wo_chapter, keep_tikz_source=args.keep_tikz_source)
        latex_doc = wrap_latex_document(body)
        try:
            id_prefix = re.sub(r"[^A-Za-z0-9]", "-", Path(stem).name) + "-"
            md = run_pandoc_latex_to_markdown(
                latex_doc,
                book_root=book_root,
                bib=bib_arg,
                id_prefix=id_prefix,
            )
        except RuntimeError as e:
            raise RuntimeError(f"Pandoc failed for {stem}: {e}") from e
        out_path = out_dir / stem_to_out_name(stem)
        write_qmd(out_path, title, postprocess_chapter_markdown(md))

    manifest_path = book_root / "website" / "chapter_gen_manifest.json"
    write_generated_manifest(manifest_path, parts=parts)
    print(f"quarto_gen: wrote {len(items)} chapters into {out_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
