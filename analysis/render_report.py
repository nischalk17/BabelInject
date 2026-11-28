"""Render report/report.md to report/report.html (and a PDF if Chrome is found).

Needs the optional `markdown` package, so run it as:
    uv run --with markdown python analysis/render_report.py
The PDF step uses a locally installed Chrome or Edge in headless mode; without one only the HTML is
written (open it and print to PDF from the browser).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import markdown  # type: ignore[import-untyped]

# ruff: noqa: E501  (the stylesheet is one long block of CSS)
CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font: 11pt/1.5 Georgia, 'Times New Roman', serif; max-width: 46rem; margin: 2rem auto; color: #111; }
h1 { font-size: 1.7rem; line-height: 1.25; } h2 { font-size: 1.3rem; margin-top: 2rem; border-bottom: 1px solid #ccc; }
h3 { font-size: 1.1rem; } code { font: 0.9em Consolas, monospace; background: #f3f3f3; padding: 0 .2em; }
pre { background: #f3f3f3; padding: .6rem; overflow-x: auto; } pre code { background: none; }
table { border-collapse: collapse; margin: 1rem 0; font-size: 0.9em; width: 100%; }
th, td { border: 1px solid #bbb; padding: .3rem .5rem; text-align: left; vertical-align: top; }
th { background: #eee; } img { max-width: 100%; display: block; margin: 1rem auto; }
table, img, pre { break-inside: avoid; } h2, h3 { break-after: avoid; }
"""
CHROME = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)


def main() -> None:
    source = Path("report/report.md")
    body = markdown.markdown(
        source.read_text(encoding="utf-8"), extensions=["tables", "fenced_code", "sane_lists"]
    )
    html = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<title>BabelInject report</title><style>"
        + CSS
        + "</style></head><body>"
        + body
        + "</body></html>"
    )
    out = source.with_suffix(".html")
    out.write_text(html, encoding="utf-8")
    print("wrote", out)
    browser = next((c for c in CHROME if Path(c).exists()), shutil.which("chrome"))
    if browser:
        pdf = source.with_suffix(".pdf").resolve()
        subprocess.run(
            [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf}",
                out.resolve().as_uri(),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        print("wrote", pdf)


if __name__ == "__main__":
    main()
