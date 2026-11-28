"""Check that every "k/n" and "k of n" in the report text matches a table in ``results/summary*/``.

A fraction matches if it equals a table cell or a pooled sum of cells (over any subset of the
grouping columns, also with the capability-control channel left out). It catches transcription slips
and numbers that went stale after a re-run; it does not check percentages, bounds or prose.
"""

from __future__ import annotations

import csv
import itertools
import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path

_KEYS = ("model_tag", "defense", "attack", "language", "channel", "metric", "condition")
_FRACTION = re.compile(r"\b(\d+)\s*(?:/|of)\s*(\d+)\b")


def known_counts(summary_dirs: Iterable[Path]) -> set[tuple[int, int]]:
    """Every (k, n) that is a table cell or a pooled sum of cells in the given summary folders."""
    known: set[tuple[int, int]] = set()
    for folder in summary_dirs:
        for csv_path in sorted(folder.glob("*.csv")):
            with csv_path.open(encoding="utf-8") as handle:
                rows = [r for r in csv.DictReader(handle) if r.get("k", "").isdigit()]
            if not rows:
                continue
            columns = [c for c in _KEYS if c in rows[0]]
            variants = [rows]
            if "channel" in columns:
                variants.append([r for r in rows if r["channel"] != "user"])
            for variant in variants:
                for size in range(len(columns) + 1):
                    for subset in itertools.combinations(columns, size):
                        sums: dict[tuple[str, ...], list[int]] = defaultdict(lambda: [0, 0])
                        for r in variant:
                            cell = sums[tuple(r[c] for c in subset)]
                            cell[0] += int(r["k"])
                            cell[1] += int(r["n"])
                        known.update((k, n) for k, n in sums.values())
    return known


def unmatched_fractions(
    files: Sequence[Path], known: set[tuple[int, int]]
) -> tuple[int, list[tuple[Path, int, int, int]]]:
    """Scan text files; return (fractions scanned, those that match no table)."""
    scanned = 0
    missing: list[tuple[Path, int, int, int]] = []
    for path in files:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for m in _FRACTION.finditer(line):
                k, n = int(m[1]), int(m[2])
                if n < 2 or k > n:  # "1 of 1", "7/5": not a count of runs
                    continue
                scanned += 1
                if (k, n) not in known:
                    missing.append((path, number, k, n))
    return scanned, missing
