"""Counts and Wilson confidence intervals over judged runs. Pure functions, no model calls."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence

from pydantic import BaseModel

from aie.eval.runner import ScenarioOutcome

Z95 = 1.959964


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval for ``k`` successes out of ``n`` trials."""
    if n <= 0 or not 0 <= k <= n:
        raise ValueError(f"need n > 0 and 0 <= k <= n, got k={k}, n={n}")
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


class Rate(BaseModel):
    """A proportion with its 95% Wilson interval."""

    k: int
    n: int
    point: float
    lo: float
    hi: float


def rate(k: int, n: int) -> Rate:
    """Build a ``Rate`` from counts."""
    lo, hi = wilson(k, n)
    return Rate(k=k, n=n, point=k / n, lo=lo, hi=hi)


class CellSummary(BaseModel):
    """One (model, language, channel) cell. Benign runs have language and channel None.

    ``asr`` is None for the benign cell. ``utility`` is the benign-task success rate (for attacked
    cells it is utility under attack).
    """

    model_tag: str
    defense: str
    language: str | None
    channel: str | None
    asr: Rate | None
    utility: Rate


def summarize(outcomes: Sequence[ScenarioOutcome]) -> list[CellSummary]:
    """Group judged outcomes by (model tag, defense, language, channel) and compute rates."""
    groups: dict[tuple[str, str, str | None, str | None], list[ScenarioOutcome]] = defaultdict(list)
    for o in outcomes:
        groups[(o.result.model_tag, o.defense, o.language, o.channel)].append(o)
    cells = []
    for (tag, defense, language, channel), rows in sorted(
        groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] or "", kv[0][3] or "")
    ):
        attacked = [r for r in rows if r.judge.attack_success is not None]
        cells.append(
            CellSummary(
                model_tag=tag,
                defense=defense,
                language=language,
                channel=channel,
                asr=rate(sum(1 for r in attacked if r.judge.attack_success), len(attacked))
                if attacked
                else None,
                utility=rate(sum(1 for r in rows if r.judge.utility_success), len(rows)),
            )
        )
    return cells


def format_cell(c: CellSummary) -> str:
    """One console line for a cell."""
    where = "benign" if c.language is None else f"{c.language}/{c.channel}"
    util = f"utility {c.utility.k}/{c.utility.n}"
    head = f"{c.model_tag} | {c.defense} | {where}"
    if c.asr is None:
        return f"{head}: {util}"
    a = c.asr
    return f"{head}: ASR {a.k}/{a.n} = {a.point:.1%} [95% CI {a.lo:.1%}, {a.hi:.1%}]  {util}"
