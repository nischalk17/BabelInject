"""Compare every fraction in the report text with the summary tables. Exit 1 on a mismatch.

Usage: uv run python analysis/check_report_numbers.py [files ...]
Default files: README.md and the report sections (not the outline or the verification notes).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aie.analysis.report_check import known_counts, unmatched_fractions

SECTIONS = [
    "abstract",
    "introduction",
    "related",
    "method",
    "results",
    "discussion",
    "conclusion",
    "reproducibility",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path)
    args = parser.parse_args()
    files = args.files or [Path("README.md"), *(Path("report") / f"{s}.md" for s in SECTIONS)]
    known = known_counts(sorted(Path("results").glob("summary*")))
    scanned, missing = unmatched_fractions([f for f in files if f.exists()], known)
    for path, line, k, n in missing:
        print(f"{path}:{line}: {k}/{n} matches no table cell or pooled sum")
    print(f"{scanned} fractions checked; {len(missing)} without a matching table value")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
