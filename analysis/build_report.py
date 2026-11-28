"""Write report/report.md from the section files. Usage: uv run python analysis/build_report.py."""

from __future__ import annotations

from pathlib import Path

from aie.analysis.report_build import assemble

AUTHOR = "Nischal Dhoj Kunwar"
DATE = "28 November 2026"
REPO = "https://github.com/nischalk17/BabelInject"


def main() -> None:
    out = Path("report/report.md")
    out.write_text(assemble(Path("report"), AUTHOR, DATE, REPO), encoding="utf-8", newline="\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
