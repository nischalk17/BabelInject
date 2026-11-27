"""Data files for the static Results Explorer demo, built only from ``results/``.

Every number comes from the functions in :mod:`aie.analysis.tables` (the same ones that write the
summary CSVs); nothing is recomputed here. Output is deterministic: sorted keys, rounded floats, LF
line endings and no wall-clock time, so exporting the same results twice gives identical bytes.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from aie.analysis.load import LoadReport, load_outcomes
from aie.analysis.tables import (
    CountRow,
    answer_mention_rows,
    asr_rows,
    attacked_utility_rows,
    attempt_rows,
    benign,
    benign_flagged_rows,
    effect_rows,
    flagged_rows,
    opened_rows,
    utility_rows,
)
from aie.eval.runner import ScenarioOutcome
from aie.scenarios.schema import load_attacks

SCHEMA_VERSION = 1
ROUND = 6


class StudyConfig(BaseModel):
    """One study: a set of results folders summarised together (never pooled with another study)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    attacks_file: Path
    inputs: list[Path]


class DemoConfig(BaseModel):
    """``configs/demo_studies.yaml``."""

    model_config = ConfigDict(extra="forbid")

    repo_url: str
    report_url: str
    studies: list[StudyConfig]


def load_demo_config(path: Path) -> DemoConfig:
    """Load and validate the studies config."""
    return DemoConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def _clean(obj: Any) -> Any:
    """Round floats so the JSON text is stable across platforms."""
    if isinstance(obj, float):
        return round(obj, ROUND)
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj


def _stat(row: BaseModel) -> dict[str, Any]:
    d = row.model_dump()
    return {key: d[key] for key in ("k", "n", "rate", "lo", "hi")}


def _count_dict(row: CountRow) -> dict[str, Any]:
    return {"model_tag": row.model_tag, "defense": row.defense, "language": row.language,
            "channel": row.channel, "metric": row.metric, **_stat(row)}  # fmt: skip


def _by_cell(rows: Sequence[CountRow]) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    return {(r.model_tag, r.defense, r.language, r.channel): _stat(r) for r in rows}


def _study_cells(
    outcomes: Sequence[ScenarioOutcome], attackers: dict[str, str]
) -> list[dict[str, Any]]:
    """ASR per cell for every defense; the pooled "ALL" cells also carry the cell-level extras.

    ``attacked_utility``, ``item_opened`` and ``attack_attempted`` are defined per (model, defense,
    language, channel), not per attack, so they sit on the "ALL" cell only.
    """
    defenses = sorted({o.defense for o in outcomes})
    utility = _by_cell(attacked_utility_rows(outcomes))
    opened = _by_cell(opened_rows(outcomes))
    attempted = _by_cell(attempt_rows(outcomes, attackers))
    return [
        {
            "model_tag": r.model_tag,
            "defense": r.defense,
            "attack": r.attack,
            "language": r.language,
            "channel": r.channel,
            "asr": _stat(r),
            **(
                {
                    "attacked_utility": utility.get(key),
                    "item_opened": opened.get(key),
                    "attack_attempted": attempted.get(key),
                }
                if r.attack == "ALL"
                else {}
            ),
        }
        for d in defenses
        for r in asr_rows(outcomes, d)
        for key in [(r.model_tag, r.defense, r.language, r.channel)]
    ]


def build_study(
    study: StudyConfig,
    outcomes: Sequence[ScenarioOutcome],
    report: LoadReport,
    attacks_file: Path,
) -> dict[str, Any]:
    """Summary for one study, using the analysis functions unchanged.

    ``attacks_file`` is the resolved path to read the attacker recipients from; ``report.files`` is
    stored as given, so pass paths relative to the repository root for a portable file.
    """
    attackers = {a.id: a.goal.to for a in load_attacks(attacks_file)}
    utility = utility_rows(outcomes)
    out: dict[str, Any] = {
        "id": study.id,
        "title": study.title,
        "status": "ok",
        "attacks_file": study.attacks_file.as_posix(),
        "inputs": [p.as_posix() for p in study.inputs],
        "load_report": {
            "files": [Path(f).as_posix() for f in report.files],
            "rows_read": report.rows_read,
            "duplicates_dropped": report.duplicates_dropped,
            "rows_kept": report.rows_kept,
        },
        "cells": _study_cells(outcomes, attackers),
        "benign": [
            {"model_tag": r.model_tag, "defense": r.defense, "utility": _stat(r)}
            for r in utility
            if r.condition == "benign"
        ],
        "effects": [r.model_dump() for r in effect_rows(outcomes)],
        "metrics": {},
    }
    metrics: dict[str, list[CountRow]] = {
        "answer_mentions_injection": answer_mention_rows(outcomes)
    }
    if any(o.defense == "detector" for o in outcomes):
        metrics["detector_flagged"] = flagged_rows(outcomes)
        if benign(outcomes):
            metrics["detector_flagged_benign"] = benign_flagged_rows(outcomes)
    out["metrics"] = {
        name: [_count_dict(r) for r in rows] for name, rows in metrics.items() if rows
    }
    return out


def _empty_study(study: StudyConfig) -> dict[str, Any]:
    return {
        "id": study.id,
        "title": study.title,
        "status": "not_run",
        "attacks_file": study.attacks_file.as_posix(),
        "inputs": [p.as_posix() for p in study.inputs],
        "cells": [],
        "benign": [],
        "effects": [],
        "metrics": {},
    }


def _run_info(files: Sequence[str]) -> dict[str, dict[str, Any]]:
    """Per model tag: raw rows read and the first and last run date (from ``started_at``)."""
    info: dict[str, dict[str, Any]] = {}
    for f in files:
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            tag = row["result"]["model_tag"]
            day = str(row.get("started_at", ""))[:10]
            entry = info.setdefault(tag, {"rows": 0, "days": set()})
            entry["rows"] += 1
            if day:
                entry["days"].add(day)
    return info


def git_commit(root: Path) -> str:
    """The commit the export was generated on top of, or ``"unknown"`` outside a git checkout."""
    try:
        done = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return done.stdout.strip() or "unknown"


def build_summary_and_meta(
    cfg: DemoConfig, root: Path, commit: str | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build ``summary.json`` and ``meta.json`` content from the folders named in ``cfg``."""
    studies: list[dict[str, Any]] = []
    all_files: list[str] = []
    rows_by_study: dict[str, int] = {}
    for study in cfg.studies:
        try:
            outcomes, report = load_outcomes([root / p for p in study.inputs])
        except ValueError:
            studies.append(_empty_study(study))
            rows_by_study[study.id] = 0
            continue
        rel = report.model_copy(
            update={"files": [Path(f).relative_to(root).as_posix() for f in report.files]}
        )
        studies.append(build_study(study, outcomes, rel, root / study.attacks_file))
        all_files += report.files
        rows_by_study[study.id] = report.rows_kept
    info = _run_info(sorted(set(all_files)))
    models = [
        {
            "tag": tag,
            "provider": tag.split("/", 1)[0],
            "rows_read": v["rows"],
            "first_run": min(v["days"]) if v["days"] else None,
            "last_run": max(v["days"]) if v["days"] else None,
        }
        for tag, v in sorted(info.items())
    ]
    summary = {"schema_version": SCHEMA_VERSION, "studies": studies}
    meta = {
        "schema_version": SCHEMA_VERSION,
        "git_commit": commit if commit is not None else git_commit(root),
        "repo_url": cfg.repo_url,
        "report_url": cfg.report_url,
        "models": models,
        "scenarios_by_study": rows_by_study,
    }
    return _clean(summary), _clean(meta)


def dumps(obj: Any) -> str:
    """Stable JSON text (sorted keys, 1-space indent, trailing newline)."""
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def write_json(path: Path, obj: Any) -> None:
    """Write JSON with LF line endings on every platform."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(dumps(obj).encode("utf-8"))


def export(cfg: DemoConfig, root: Path, out_dir: Path, commit: str | None = None) -> list[Path]:
    """Write ``summary.json`` and ``meta.json`` into ``out_dir``; return the written paths."""
    summary, meta = build_summary_and_meta(cfg, root, commit)
    paths = [out_dir / "summary.json", out_dir / "meta.json"]
    write_json(paths[0], summary)
    write_json(paths[1], meta)
    return paths
