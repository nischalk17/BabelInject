"""Command line entry point: ``aie run configs/mvp.yaml``."""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from aie.config import ExperimentConfig, load_config
from aie.eval.metrics import format_cell, summarize
from aie.eval.runner import ScenarioOutcome, run_scenario
from aie.models.base import ModelAdapter
from aie.models.cache import build_model
from aie.scenarios.grid import SkippedCell, build_grid
from aie.scenarios.schema import Scenario, load_attacks, load_tasks

app = typer.Typer(help="Prompt-injection evaluation for tool-using LLM agents.")


@app.callback()
def _main() -> None:
    """Prompt-injection evaluation for tool-using LLM agents."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:  # Devanagari output on Windows consoles
        reconfigure(encoding="utf-8")


def plan_run(cfg: ExperimentConfig) -> tuple[list[Scenario], list[SkippedCell]]:
    """Load the task and attack libraries and expand the config into scenarios."""
    tasks = load_tasks(cfg.tasks_file)
    attacks = load_attacks(cfg.attacks_file)
    return build_grid(cfg, tasks, attacks)


def make_row(
    cfg: ExperimentConfig, config_name: str, outcome: ScenarioOutcome
) -> dict[str, object]:
    """One JSONL row: the outcome plus the settings needed to audit it."""
    return {
        "config_name": config_name,
        "started_at": datetime.now().isoformat(timespec="seconds"),  # hosted models can drift
        "gen": cfg.gen.model_dump(mode="json"),
        **outcome.model_dump(mode="json"),
    }


def run_models(
    cfg: ExperimentConfig,
    scenarios: list[Scenario],
    models: list[ModelAdapter],
    config_name: str,
    out_path: Path,
) -> list[ScenarioOutcome]:
    """Run every scenario on every model, appending each judged row to ``out_path`` as it ends."""
    outcomes: list[ScenarioOutcome] = []
    total = len(models) * len(scenarios)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for model in models:
            for scenario in scenarios:
                outcome = run_scenario(model, scenario, cfg=cfg.gen, max_steps=cfg.max_steps)
                outcomes.append(outcome)
                f.write(json.dumps(make_row(cfg, config_name, outcome), ensure_ascii=False) + "\n")
                f.flush()
                j = outcome.judge
                typer.echo(
                    f"[{len(outcomes)}/{total}] {outcome.result.model_tag} {scenario.id} "
                    f"attack_success={j.attack_success} utility={j.utility_success}"
                )
    return outcomes


@app.command()
def run(config: Annotated[Path, typer.Argument(exists=True, dir_okay=False)]) -> None:
    """Run the experiment described by CONFIG and write judged JSONL rows to results/."""
    cfg = load_config(config)
    scenarios, skipped = plan_run(cfg)
    if not scenarios:
        raise typer.BadParameter("the config expands to zero scenarios")
    skipped_by_channel = Counter(s.channel for s in skipped)
    for channel, count in sorted(skipped_by_channel.items()):
        typer.echo(f"skipped {count} cell(s) for channel {channel!r}: task has no injection point")
    models = [build_model(m, cfg.cache_path) for m in cfg.models]
    out = cfg.output_dir / f"{config.stem}-{datetime.now():%Y%m%dT%H%M%S}.jsonl"
    outcomes = run_models(cfg, scenarios, models, config.name, out)
    typer.echo("")
    for cell in summarize(outcomes):
        typer.echo(format_cell(cell))
    typer.echo(f"wrote {out}")
