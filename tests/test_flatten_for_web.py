"""Tests for website/flatten_for_web.py helpers."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

_BOOK = Path(__file__).resolve().parents[1]
_FLATTEN = _BOOK / "website" / "flatten_for_web.py"


def _load_flatten():
    spec = importlib.util.spec_from_file_location("flatten_for_web", _FLATTEN)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ff = _load_flatten()


class TestFlattenHelpers(unittest.TestCase):
    def test_strip_endinput_removes_lines(self):
        tex = "a\n\\endinput\nb\n\\endinput % trailing\n"
        self.assertEqual(ff.strip_endinput(tex), "a\nb\n")

    def test_fullwidth_figure_labels(self):
        tex = r"""
\begin{figure*}
  \includegraphics{x}
  \caption{c}
  \label{fig:wide-one}
\end{figure*}
other
\begin{figure*}
\label{fig:wide-two}
\end{figure*}
"""
        self.assertEqual(
            ff.fullwidth_figure_labels(tex),
            ["fig:wide-one", "fig:wide-two"],
        )

    def test_write_fullwidth_metadata_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "fw.json"
            ff.write_fullwidth_metadata(p, ["fig:a", "fig:b"])
            data = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(data, {"fullwidth-figures": ["fig:a", "fig:b"]})

    def test_algorithm_environments_to_verbatim(self):
        tex = r"""
\begin{algorithm}[H]
\KwIn{x}
\end{algorithm}
after
"""
        out = ff.algorithm_environments_to_verbatim(tex)
        self.assertIn(r"\begin{verbatim}", out)
        self.assertIn("WEB-ALGORITHM-BEGIN", out)
        self.assertNotIn(r"\begin{algorithm}", out)

    def test_tikzpicture_placeholder(self):
        tex = r"\begin{tikzpicture}\draw (0,0);\end{tikzpicture}"
        short = ff.tikzpicture_environments_to_placeholder(tex, keep_source=False)
        self.assertIn("Illustration omitted", short)
        self.assertNotIn("tikzpicture", short)
        long = ff.tikzpicture_environments_to_placeholder(tex, keep_source=True)
        self.assertIn(r"\draw (0,0)", long)

    def test_marginfigure_promotes_caption_to_quote(self):
        tex = r"""
\begin{marginfigure}
  \includegraphics[width=\linewidth]{figures/x.png}
  \caption{The three conformations: $\alpha$ and $\beta$.}
  \label{fig:x}
\end{marginfigure}
"""
        out = ff.replace_balanced_environment(
            tex,
            "marginfigure",
            ff.marginfigure_promote_captions_inner,
        )
        self.assertIn(r"\begin{quote}\small", out)
        self.assertIn(r"The three conformations: $\alpha$ and $\beta$.", out)
        self.assertNotIn(r"\caption{", out)
        self.assertNotIn(r"\label{fig:x}", out)

    def test_marginfigure_without_caption_unchanged(self):
        tex = r"\begin{marginfigure}\includegraphics{x}\end{marginfigure}"
        out = ff.replace_balanced_environment(
            tex,
            "marginfigure",
            ff.marginfigure_promote_captions_inner,
        )
        self.assertIn(r"\begin{marginfigure}", out)
        self.assertIn(r"\includegraphics{x}", out)
        self.assertIn(r"\end{marginfigure}", out)
        self.assertNotIn(r"\begin{quote}", out)

    def test_marginfigure_optional_short_caption(self):
        tex = (
            r"\begin{marginfigure}"
            r"\includegraphics{x}"
            r"\caption[short]{Long visible text.}"
            r"\end{marginfigure}"
        )
        out = ff.replace_balanced_environment(
            tex,
            "marginfigure",
            ff.marginfigure_promote_captions_inner,
        )
        self.assertIn("Long visible text.", out)
        self.assertNotIn(r"\caption", out)

    def test_flatten_cli_produces_merged_and_fullwidth(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "merged.tex"
            fw = tmp_path / "fw.json"
            subprocess.run(
                [
                    "python3",
                    str(_FLATTEN),
                    "--book-root",
                    str(_BOOK),
                    "--output",
                    str(out),
                    "--fullwidth-json",
                    str(fw),
                ],
                check=True,
            )
            body = out.read_text(encoding="utf-8")
            self.assertEqual(body.count(r"\chapter{"), 12)
            self.assertNotIn("\\endinput", body)
            self.assertTrue(fw.is_file())
            data = json.loads(fw.read_text(encoding="utf-8"))
            self.assertIn("fullwidth-figures", data)
            self.assertGreaterEqual(len(data["fullwidth-figures"]), 1)


if __name__ == "__main__":
    unittest.main()
