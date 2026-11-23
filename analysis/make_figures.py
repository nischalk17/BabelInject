"""Write the figures from results/. Usage: uv run python analysis/make_figures.py."""

from __future__ import annotations

import argparse
from pathlib import Path

from aie.analysis.report import build_figures, describe

DEFAULT_INPUTS = ["results/full", "results/defenses", "results/hosted", "results/full_3b"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="+", type=Path, default=[Path(p) for p in DEFAULT_INPUTS])
    parser.add_argument("--out", type=Path, default=Path("docs/figures"))
    args = parser.parse_args()
    paths, report = build_figures(args.inputs, args.out)
    print(describe(report))
    for path in paths:
        print("wrote", path)


if __name__ == "__main__":
    main()
