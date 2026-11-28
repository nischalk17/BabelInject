from pathlib import Path

import pytest

from aie.analysis.report_build import PARTS, assemble, demote_headings, strip_status


def test_status_paragraphs_are_dropped_and_headings_demoted() -> None:
    text = "# 2. Related\n\n**Status:** draft note.\n\nBody text.\n"
    assert strip_status(text) == "# 2. Related\n\nBody text."
    fenced = "# Title\n```\n# comment in code\n```\n## Sub"
    assert demote_headings(fenced) == "## Title\n```\n# comment in code\n```\n### Sub"


def make_parts(folder: Path, extra: str = "") -> None:
    for part in PARTS:
        (folder / f"{part}.md").write_text(f"# {part}\n\ntext {extra}\n", encoding="utf-8")


def test_assemble_joins_all_parts_in_order(tmp_path: Path) -> None:
    make_parts(tmp_path)
    doc = assemble(tmp_path, "A. Author", "1 January 2027", "https://example.test")
    assert doc.startswith("# BabelInject")
    order = [doc.index(f"## {p}\n") for p in PARTS]
    assert order == sorted(order)


def test_leftover_draft_markers_are_refused(tmp_path: Path) -> None:
    make_parts(tmp_path, extra="(first draft)")
    with pytest.raises(ValueError, match="draft marker"):
        assemble(tmp_path, "A", "d", "u")


def test_the_real_report_assembles_without_draft_markers() -> None:
    repo = Path(__file__).resolve().parent.parent
    doc = assemble(repo / "report", "A", "d", "u")
    assert "## Abstract" in doc and "## References" in doc and "Table E" in doc
