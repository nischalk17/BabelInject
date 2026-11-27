"""Write the Results Explorer demo data. Usage: uv run python analysis/export_demo_data.py."""

from __future__ import annotations

import argparse
from pathlib import Path

from aie.analysis.demo_export import export, load_demo_config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/demo_studies.yaml"))
    parser.add_argument("--out", type=Path, default=Path("demo/public/data"))
    args = parser.parse_args()
    for path in export(load_demo_config(args.config), Path.cwd(), args.out):
        print("wrote", path)


if __name__ == "__main__":
    main()
