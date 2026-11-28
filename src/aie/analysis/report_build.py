"""Assemble ``report/report.md`` from the section files (one source of truth per section)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

PARTS = (
    "abstract",
    "introduction",
    "related",
    "method",
    "results",
    "discussion",
    "conclusion",
    "reproducibility",
    "references",
    "appendix",
)

TITLE = (
    "BabelInject: Do Prompt-Injection Defenses for Tool-Using LLM Agents Hold Across Languages "
    "and Injection Channels?"
)
SUBTITLE = "A small-model study in English, Nepali, romanized Nepali, Hindi and code-mixed text"
_DRAFT_MARKERS = ("(first draft", "Status: draft", "PENDING", "TODO", "TBD")


def strip_status(text: str) -> str:
    """Drop the working-note paragraph ("Status: ..." / "**Status:** ...") from a section."""
    paragraphs = re.split(r"\n\s*\n", text.strip("\n"))
    kept = [p for p in paragraphs if not re.match(r"\s*(\*\*)?Status:?(\*\*)?:?\s", p)]
    return "\n\n".join(kept).strip("\n")


def demote_headings(text: str) -> str:
    """Add one level to every Markdown heading, leaving fenced code blocks alone."""
    out: list[str] = []
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        out.append("#" + line if not fenced and re.match(r"#{1,5} ", line) else line)
    return "\n".join(out)


def contents(parts: Sequence[str], texts: dict[str, str]) -> str:
    """A contents list from each part's first heading."""
    lines = []
    for part in parts:
        heading = texts[part].splitlines()[0].lstrip("# ").strip()
        number, dot, rest = heading.partition(". ")
        escaped = f"{number}\\. {rest}" if dot and number.isdigit() else heading
        lines.append(f"- {escaped}")
    return "\n".join(lines)


def assemble(report_dir: Path, author: str, date: str, repo_url: str) -> str:
    """Join the parts under a title block and contents list; refuse leftover draft markers."""
    texts = {p: strip_status((report_dir / f"{p}.md").read_text(encoding="utf-8")) for p in PARTS}
    for part, text in texts.items():
        for marker in _DRAFT_MARKERS:
            if marker in text:
                raise ValueError(f"{part}.md still contains the draft marker {marker!r}")
    head = (
        f"# {TITLE}\n\n**{SUBTITLE}**\n\n{author} | {date} | {repo_url}\n\n"
        f"## Contents\n\n{contents(PARTS, texts)}\n"
    )
    body = "\n\n".join(demote_headings(texts[p]) for p in PARTS)
    return head + "\n---\n\n" + body + "\n"
