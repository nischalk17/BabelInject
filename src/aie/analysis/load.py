"""Load judged result rows from ``results/`` JSONL files, with de-duplication."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel

from aie.eval.runner import ScenarioOutcome


class LoadReport(BaseModel):
    """What was read, so every table can state where its numbers came from."""

    files: list[str]
    rows_read: int
    duplicates_dropped: int
    rows_kept: int


def expand(paths: Sequence[Path]) -> list[Path]:
    """Expand directories to their ``*.jsonl`` files; the result is sorted by name (timestamped)."""
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.glob("*.jsonl")))
        elif p.is_file():
            files.append(p)
    return sorted(files, key=lambda f: (f.name, str(f)))


def load_outcomes(paths: Sequence[Path]) -> tuple[list[ScenarioOutcome], LoadReport]:
    """Read every row and drop repeats of the same (model, defense, scenario).

    If the same scenario was run twice (a re-run), the row from the later file wins, so no
    scenario is ever counted twice. Raises ``ValueError`` if nothing was found.
    """
    files = expand(paths)
    kept: dict[tuple[str, str, str], ScenarioOutcome] = {}
    read = 0
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            outcome = ScenarioOutcome.model_validate(json.loads(line))
            read += 1
            kept[(outcome.result.model_tag, outcome.defense, outcome.scenario_id)] = outcome
    if not kept:
        raise ValueError(f"no result rows found in {[str(p) for p in paths]}")
    report = LoadReport(
        files=[str(f) for f in files],
        rows_read=read,
        duplicates_dropped=read - len(kept),
        rows_kept=len(kept),
    )
    return list(kept.values()), report
