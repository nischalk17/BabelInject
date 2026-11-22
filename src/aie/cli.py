"""Command line entry point: ``aie run configs/smoke.yaml``."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from aie.agent.loop import run_agent
from aie.config import RunConfig, load_config
from aie.env.sandbox import Sandbox
from aie.models.base import ModelAdapter
from aie.models.cache import build_model

app = typer.Typer(help="Prompt-injection evaluation for tool-using LLM agents.")


@app.callback()
def _main() -> None:
    """Prompt-injection evaluation for tool-using LLM agents."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:  # Devanagari output on Windows consoles
        reconfigure(encoding="utf-8")


def execute(cfg: RunConfig, model: ModelAdapter, config_name: str) -> dict[str, Any]:
    """Run the configured task once and return one result row (JSON-serializable)."""
    sandbox = Sandbox.from_yaml(cfg.sandbox)
    result = run_agent(
        model,
        sandbox,
        cfg.task,
        tools=cfg.tools,
        cfg=cfg.gen,
        max_steps=cfg.max_steps,
    )
    return {
        "config_name": config_name,
        "config": cfg.model_dump(mode="json"),
        "task": cfg.task,
        **result.model_dump(mode="json"),
        "outbox": [e.model_dump() for e in sandbox.outbox],
    }


def write_row(row: dict[str, Any], output_dir: Path, stem: str) -> Path:
    """Append the row as one JSONL line to a new timestamped file and return its path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{stem}-{datetime.now():%Y%m%dT%H%M%S}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


@app.command()
def run(config: Annotated[Path, typer.Argument(exists=True, dir_okay=False)]) -> None:
    """Run the experiment described by CONFIG and write a JSONL result row."""
    cfg = load_config(config)
    model = build_model(cfg.model, cfg.cache_path)
    row = execute(cfg, model, config.name)
    path = write_row(row, cfg.output_dir, config.stem)
    typer.echo(f"model: {row['model_tag']}  stop: {row['stop_reason']}  steps: {row['steps']}")
    for a in row["actions"]:
        typer.echo(f"  [{a['step']}] {a['tool']}({a['args']}) ok={a['ok']}")
    typer.echo(f"answer: {row['final_answer']}")
    typer.echo(f"wrote {path}")
