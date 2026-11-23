"""Write the summary CSVs (table views) from results/. Usage: uv run python analysis/tables.py."""

from __future__ import annotations

import argparse
from pathlib import Path

from aie.analysis.report import build_tables, describe

DEFAULT_INPUTS = ["results/full", "results/defenses", "results/hosted", "results/full_3b"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="+", type=Path, default=[Path(p) for p in DEFAULT_INPUTS])
    parser.add_argument("--out", type=Path, default=Path("results/summary"))
    parser.add_argument("--attacks", type=Path, default=Path("src/aie/scenarios/attacks.yaml"))
    args = parser.parse_args()
    written, report = build_tables(args.inputs, args.out, args.attacks)
    print(describe(report))
    for path in written:
        print("wrote", path)


if __name__ == "__main__":
    main()
