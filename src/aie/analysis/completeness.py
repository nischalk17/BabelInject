"""Did a config's grid finish? Compare the scenarios a config expands to with the rows on disk.

A crashed run or an exhausted hosted quota otherwise shows up only as a smaller n in some table.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path

from pydantic import BaseModel

from aie.analysis.load import expand


class CellCompleteness(BaseModel):
    """Rows found for one (model, defense) against the rows the config asks for."""

    model_tag: str
    defense: str
    expected: int
    found: int
    missing: list[str]
    unexpected: int

    @property
    def complete(self) -> bool:
        """True when every expected scenario has a row."""
        return not self.missing


class Completeness(BaseModel):
    """Result of checking one config; ``models_missing`` counts configured models with no rows."""

    config_name: str
    cells: list[CellCompleteness]
    models_expected: int
    models_missing: int

    @property
    def complete(self) -> bool:
        """True when every configured model has rows and no cell is missing a scenario."""
        return self.models_missing == 0 and all(c.complete for c in self.cells)


def check_completeness(
    config_name: str,
    expected_ids: Sequence[str],
    defenses: Sequence[str],
    models_expected: int,
    result_paths: Iterable[Path],
) -> Completeness:
    """Compare the expected scenario ids with the rows whose ``config_name`` matches.

    Rows are matched on (model tag, defense, scenario id); a scenario re-run later counts once.
    Rows of other configs in the same folder are ignored.
    """
    found: dict[tuple[str, str], set[str]] = defaultdict(set)
    for f in expand(list(result_paths)):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("config_name") != config_name:
                continue
            found[(row["result"]["model_tag"], row.get("defense", "none"))].add(row["scenario_id"])
    wanted = set(expected_ids)
    cells = [
        CellCompleteness(
            model_tag=tag,
            defense=defense,
            expected=len(wanted),
            found=len(ids & wanted),
            missing=sorted(wanted - ids),
            unexpected=len(ids - wanted),
        )
        for (tag, defense), ids in sorted(found.items())
    ]
    seen_models = {c.model_tag for c in cells}
    # A defense with no rows for a model that did run is missing as a whole cell.
    for tag in sorted(seen_models):
        for defense in defenses:
            if (tag, defense) not in found:
                cells.append(
                    CellCompleteness(
                        model_tag=tag,
                        defense=defense,
                        expected=len(wanted),
                        found=0,
                        missing=sorted(wanted),
                        unexpected=0,
                    )
                )
    return Completeness(
        config_name=config_name,
        cells=cells,
        models_expected=models_expected,
        models_missing=max(0, models_expected - len(seen_models)),
    )


def format_completeness(c: Completeness) -> str:
    """Human-readable report, one line per cell; names the first missing scenario."""
    lines = [f"{c.config_name}: {'complete' if c.complete else 'INCOMPLETE'}"]
    if c.models_missing:
        lines.append(
            f"  {c.models_missing} of {c.models_expected} configured model(s) have no rows"
        )
    for cell in c.cells:
        status = (
            "ok" if cell.complete else f"missing {len(cell.missing)} (first: {cell.missing[0]})"
        )
        extra = f", {cell.unexpected} not in the config" if cell.unexpected else ""
        lines.append(
            f"  {cell.model_tag} | {cell.defense}: {cell.found}/{cell.expected} {status}{extra}"
        )
    return "\n".join(lines)
