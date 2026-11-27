"""Orchestration: results/ -> summary CSVs (table views) and figures."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from aie.analysis.figures import fig_asr_heatmap, fig_defense_effect, fig_tradeoff
from aie.analysis.load import LoadReport, load_outcomes
from aie.analysis.tables import (
    answer_mention_rows,
    asr_rows,
    attacked_utility_rows,
    attempt_rows,
    benign_flagged_rows,
    effect_rows,
    flagged_rows,
    opened_rows,
    utility_rows,
    write_csv,
)
from aie.eval.runner import ScenarioOutcome
from aie.scenarios.schema import load_attacks


def _attackers(attacks_file: Path) -> dict[str, str]:
    return {a.id: a.goal.to for a in load_attacks(attacks_file)}


def _defenses(outcomes: Sequence[ScenarioOutcome]) -> set[str]:
    return {o.defense for o in outcomes}


def build_tables(
    inputs: Sequence[Path], out_dir: Path, attacks_file: Path
) -> tuple[list[Path], LoadReport]:
    """Write every summary CSV and ``load_report.json`` (provenance); return the written paths."""
    outcomes, report = load_outcomes(inputs)
    written: list[Path] = []

    def put(name: str, rows: Sequence[object]) -> None:
        path = out_dir / name
        write_csv(path, rows)  # type: ignore[arg-type]
        written.append(path)

    put("table1_asr_language_channel.csv", asr_rows(outcomes, "none"))
    defenses = sorted(_defenses(outcomes) - {"none"})
    if defenses:
        put("table2_defense_effect.csv", effect_rows(outcomes))
        put(
            "table2b_asr_by_defense.csv",
            [r for d in sorted(_defenses(outcomes)) for r in asr_rows(outcomes, d)],
        )
    put("table3_utility.csv", utility_rows(outcomes))
    put("table4_item_opened.csv", opened_rows(outcomes))
    put("table5_attack_attempted.csv", attempt_rows(outcomes, _attackers(attacks_file)))
    put("table8_answer_mentions_injection.csv", answer_mention_rows(outcomes))
    put("table9_attacked_utility.csv", attacked_utility_rows(outcomes))
    if "detector" in defenses:
        put("table6_detector_flagged.csv", flagged_rows(outcomes))
        if benign_rows := benign_flagged_rows(outcomes):
            put("table7_detector_benign_flagged.csv", benign_rows)
    prov = out_dir / "load_report.json"
    prov.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    written.append(prov)
    return written, report


def build_figures(inputs: Sequence[Path], out_dir: Path) -> tuple[list[Path], LoadReport]:
    """Write the figures that the loaded data supports; return the written paths."""
    outcomes, report = load_outcomes(inputs)
    paths = fig_asr_heatmap(asr_rows(outcomes, "none"), out_dir)
    effects = effect_rows(outcomes)
    if effects:
        paths += fig_defense_effect(effects, out_dir)
        paths += fig_tradeoff(effects, out_dir)
    return paths, report


def describe(report: LoadReport) -> str:
    """One line saying what was read."""
    return (
        f"read {report.rows_read} rows from {len(report.files)} file(s); "
        f"dropped {report.duplicates_dropped} duplicate(s); kept {report.rows_kept}"
    )
