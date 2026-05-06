#!/usr/bin/env python3
"""Flatten tufte-book sources into a single LaTeX fragment for Pandoc HTML."""
from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable
from pathlib import Path

INCLUDE_RE = re.compile(r"\\include\{([^}]+)\}")
FIG_STAR_BLOCK = re.compile(r"\\begin\{figure\*\}(.*?)\\end\{figure\*\}", re.DOTALL)


def read_tex(book_root: Path, rel_stem: str) -> str:
    path = book_root / f"{rel_stem}.tex"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


def replace_sidenote(tex: str) -> str:
    """Replace \\sidenote{...} with \\footnote{...} using brace matching."""
    out: list[str] = []
    i = 0
    pat = re.compile(r"\\sidenote")
    while i < len(tex):
        m = pat.search(tex, i)
        if not m:
            out.append(tex[i:])
            break
        out.append(tex[i : m.start()])
        j = m.end()
        while j < len(tex) and tex[j].isspace():
            j += 1
        if j >= len(tex) or tex[j] != "{":
            out.append(tex[m.start() : j])
            i = j
            continue
        depth = 0
        k = j
        while k < len(tex):
            ch = tex[k]
            if ch == "\\" and k + 1 < len(tex):
                k += 2
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    inner = tex[j + 1 : k]
                    out.append("\\footnote{" + inner + "}")
                    i = k + 1
                    break
            k += 1
        else:
            out.append(tex[m.start() :])
            break
    return "".join(out)


def replace_part(tex: str) -> str:
    def repl(m: re.Match[str]) -> str:
        title = m.group(1).strip()
        return (
            "\\begin{center}\\Large\\bfseries "
            + title
            + "\\end{center}\\par\\medskip\n"
        )

    return re.sub(r"\\part\{([^}]*)\}", repl, tex)


def replace_cref(tex: str) -> str:
    tex = re.sub(r"\\cref\{([^}]+)\}", r"\\ref{\1}", tex)
    tex = re.sub(r"\\Cref\{([^}]+)\}", r"\\ref{\1}", tex)
    return tex


def _consume_optional_square_bracket(tex: str, idx: int) -> int:
    """If tex[idx] == '[', skip a balanced [...] slice and return the following index."""
    if idx >= len(tex) or tex[idx] != "[":
        return idx
    depth = 0
    i = idx
    while i < len(tex):
        ch = tex[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return idx


def _after_begin_environment(tex: str, begin_idx: int, env: str) -> int:
    """begin_idx points at the start of \\\\begin{env}; return index at start of inner body."""
    prefix = f"\\begin{{{env}}}"
    if not tex.startswith(prefix, begin_idx):
        msg = f"expected {prefix} at {begin_idx}"
        raise ValueError(msg)
    return _consume_optional_square_bracket(tex, begin_idx + len(prefix))


_CAPTION_CMD = re.compile(r"\\caption\b")


def _skip_latex_whitespace(tex: str, idx: int) -> int:
    while idx < len(tex) and tex[idx].isspace():
        idx += 1
    return idx


def _consume_balanced_square_brackets(tex: str, idx: int) -> int:
    """If tex[idx] is '[', return the index after the matching ']' (supports nesting)."""
    if idx >= len(tex) or tex[idx] != "[":
        return idx
    depth = 0
    i = idx
    while i < len(tex):
        ch = tex[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return idx


def marginfigure_promote_captions_inner(inner: str) -> str:
    """
    Pandoc drops \\\\caption inside marginfigure (only the image survives).

    Strip \\\\caption[short]{long} bodies, remove \\\\label{...}, and append the caption
    text as \\\\begin{quote}\\\\small ... \\\\end{quote} so the AST keeps a block under the image.
    """
    captions: list[str] = []
    i = 0
    parts: list[str] = []
    while True:
        m = _CAPTION_CMD.search(inner, i)
        if not m:
            parts.append(inner[i:])
            break
        parts.append(inner[i : m.start()])
        j = _skip_latex_whitespace(inner, m.end())
        j = _consume_balanced_square_brackets(inner, j)
        j = _skip_latex_whitespace(inner, j)
        if j >= len(inner) or inner[j] != "{":
            parts.append(inner[m.start() :])
            break
        depth = 0
        k = j
        while k < len(inner):
            ch = inner[k]
            if ch == "\\" and k + 1 < len(inner):
                k += 2
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    captions.append(inner[j + 1 : k])
                    i = k + 1
                    break
            k += 1
        else:
            parts.append(inner[m.start() :])
            break
    body = "".join(parts)
    if not captions:
        return f"\\begin{{marginfigure}}\n{inner.rstrip()}\n\\end{{marginfigure}}\n"
    body = re.sub(r"\\label\{[^}]+\}\s*", "", body)
    quote_blocks = "".join(
        f"\\begin{{quote}}\\small\n{c}\n\\end{{quote}}\n" for c in captions
    )
    inner_out = body.rstrip() + "\n" + quote_blocks
    return f"\\begin{{marginfigure}}\n{inner_out}\\end{{marginfigure}}\n"


def replace_balanced_environment(
    tex: str,
    env: str,
    replace_inner: Callable[[str], str],
) -> str:
    """
    Find \\\\begin{env}...\\\\end{env} blocks (supports nested same-env blocks)
    and substitute replace_inner(inner_tex).
    """
    begin_m = f"\\begin{{{env}}}"
    end_m = f"\\end{{{env}}}"
    out: list[str] = []
    i = 0
    while i < len(tex):
        j = tex.find(begin_m, i)
        if j == -1:
            out.append(tex[i:])
            break
        out.append(tex[i:j])
        inner_start = _after_begin_environment(tex, j, env)
        depth = 1
        search = inner_start
        while depth > 0:
            nb = tex.find(begin_m, search)
            ne = tex.find(end_m, search)
            if ne == -1:
                raise ValueError(f"unclosed LaTeX environment {env!r}")
            if nb != -1 and nb < ne:
                depth += 1
                search = _after_begin_environment(tex, nb, env)
            else:
                depth -= 1
                if depth == 0:
                    inner = tex[inner_start:ne]
                    out.append(replace_inner(inner))
                    i = ne + len(end_m)
                    break
                search = ne + len(end_m)
        else:
            raise RuntimeError(f"parse failure for environment {env!r}")
    return "".join(out)


def _verbatim_escape(inner: str) -> str:
    """Prevent inner text from closing a Pandoc \\\\end{verbatim} prematurely."""
    return inner.replace("\\end{verbatim}", "\\end {verbatim}")


def algorithm_environments_to_verbatim(tex: str) -> str:
    """
    algorithm2e is not converted to HTML by Pandoc; wrap bodies in verbatim so they
    become <pre><code> (see algorithm_codeblock.lua for class styling).
    """

    def wrap(inner: str) -> str:
        safe = _verbatim_escape(inner.strip())
        marker = "WEB-ALGORITHM-BEGIN\n"
        return (
            "\\begin{center}\\textbf{Algorithm (pseudocode)}\\end{center}\n"
            "\\begin{verbatim}\n"
            + marker
            + safe
            + "\n\\end{verbatim}\n"
        )

    # Longer environment names first so \\begin{algorithm*} does not partially match.
    for env in ("algorithm*", "algorithm"):
        tex = replace_balanced_environment(tex, env, wrap)
    return tex


def tikzpicture_environments_to_placeholder(tex: str, *, keep_source: bool) -> str:
    """TikZ is not rendered in the Pandoc HTML pipeline; omit or keep LaTeX source."""

    def wrap(inner: str) -> str:
        note = (
            "\\begin{quote}\\textit{Illustration omitted in the HTML edition; "
            "see the PDF for the TikZ figure.}\\end{quote}\n"
        )
        if not keep_source:
            return note
        safe = _verbatim_escape(inner.strip())
        return (
            note
            + "\\begin{verbatim}\n"
            + safe
            + "\n\\end{verbatim}\n"
        )

    return replace_balanced_environment(tex, "tikzpicture", wrap)


def strip_endinput(tex: str) -> str:
    """Remove \\endinput lines; Pandoc's LaTeX reader stops at the first one."""
    out_lines: list[str] = []
    for line in tex.splitlines(keepends=True):
        if line.lstrip().startswith("\\endinput"):
            continue
        out_lines.append(line)
    return "".join(out_lines)


def fullwidth_figure_labels(tex: str) -> list[str]:
    """Collect \\\\label{...} identifiers inside figure* environments for HTML styling."""
    found: list[str] = []
    for block in FIG_STAR_BLOCK.finditer(tex):
        inner = block.group(1)
        for lm in re.finditer(r"\\label\{([^}]+)\}", inner):
            found.append(lm.group(1))
    return found


def write_fullwidth_metadata(path: Path, labels: list[str]) -> None:
    path.write_text(
        json.dumps({"fullwidth-figures": labels}, indent=0) + "\n",
        encoding="utf-8",
    )


def iter_document_body(lines: list[str]):
    in_doc = False
    for line in lines:
        if not in_doc:
            if "\\begin{document}" in line:
                in_doc = True
            continue
        if "\\end{document}" in line:
            break
        yield line


def transform_chapter_body(tex: str, *, keep_tikz_source: bool = False) -> str:
    """
    Web-safe transforms for a single chapter fragment (no merged-document \\\\part lines).

    Used by the Quarto generator, which assigns book parts in ``_quarto.yml`` instead.
    """
    body = replace_cref(tex)
    body = replace_sidenote(body)
    body = replace_balanced_environment(body, "marginfigure", marginfigure_promote_captions_inner)
    body = algorithm_environments_to_verbatim(body)
    body = tikzpicture_environments_to_placeholder(body, keep_source=keep_tikz_source)
    return strip_endinput(body)


def iter_chapter_stems_with_parts(book_root: Path) -> list[tuple[str | None, str]]:
    """
    Return ordered (part_title, include_stem) pairs matching ``main.tex`` \\\\include lines.

    ``include_stem`` is the argument to ``\\\\include{...}`` without ``.tex`` (e.g.
    ``chapters/ch01_foundations``). ``part_title`` is the nearest preceding ``\\\\part{...}`` title,
    or ``None`` before the first ``\\\\part``.
    """
    main_lines = (book_root / "main.tex").read_text(encoding="utf-8").splitlines()
    current_part: str | None = None
    out: list[tuple[str | None, str]] = []
    for line in iter_document_body(main_lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("%"):
            continue
        if stripped.startswith("\\maketitle") or stripped.startswith("\\tableofcontents"):
            continue
        if stripped.startswith("\\printbibliography"):
            continue
        pm = re.match(r"\\part\{([^}]*)\}", stripped)
        if pm:
            current_part = pm.group(1).strip() or None
            continue
        m = INCLUDE_RE.match(stripped)
        if m:
            out.append((current_part, m.group(1)))
    return out


def flatten_merged_body(book_root: Path, *, keep_tikz_source: bool = False) -> str:
    """
    Build the legacy merged LaTeX fragment (with ``\\\\part`` and include markers).

    Used by ``website/build.sh``; kept for the Pandoc chunk pipeline.
    """
    root = book_root.resolve()
    main_lines = (root / "main.tex").read_text(encoding="utf-8").splitlines()

    chunks: list[str] = []
    for line in iter_document_body(main_lines):
        stripped = line.strip()
        m = INCLUDE_RE.match(stripped)
        if m:
            stem = m.group(1)
            sub = read_tex(root, stem)
            chunks.append(f"% --- included from {stem}.tex ---\n")
            chunks.append(sub)
            if not sub.endswith("\n"):
                chunks.append("\n")
            continue
        if stripped.startswith("\\maketitle"):
            continue
        if stripped.startswith("\\tableofcontents"):
            continue
        if stripped.startswith("\\printbibliography"):
            continue
        chunks.append(line + "\n")

    body = "".join(chunks)
    body = replace_part(body)
    body = transform_chapter_body(body, keep_tikz_source=keep_tikz_source)
    return body


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument(
        "--fullwidth-json",
        type=Path,
        help="Write Pandoc metadata JSON listing figure* labels (for Tufte fullwidth CSS).",
    )
    ap.add_argument(
        "--keep-tikz-source",
        action="store_true",
        help=(
            "Append TikZ source inside verbatim blocks after the omission note "
            "(large HTML; default is note-only)."
        ),
    )
    args = ap.parse_args()
    root = args.book_root.resolve()
    body = flatten_merged_body(root, keep_tikz_source=args.keep_tikz_source)

    header = (
        "% Pandoc web fragment (do not run through pdflatex)\n"
        "\\newcommand{\\newthought}[1]{\\textbf{<<NT>>#1}}\n\n"
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(header + body, encoding="utf-8")

    fw_path = args.fullwidth_json
    if fw_path is not None:
        fw_path.parent.mkdir(parents=True, exist_ok=True)
        write_fullwidth_metadata(fw_path, fullwidth_figure_labels(body))


if __name__ == "__main__":
    main()
