"""Experiment config loaded from ``configs/*.yaml``. Nothing about a run is hardcoded in code."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from aie.models.base import GenConfig, ModelConfig


class RunConfig(BaseModel):
    """One single-task run (the smoke test); grids come with the MVP config."""

    model_config = ConfigDict(extra="forbid")

    model: ModelConfig
    gen: GenConfig = Field(default_factory=GenConfig)
    sandbox: Path
    task: str
    tools: list[str] | None = None
    max_steps: int = 8
    cache_path: Path = Path(".cache/responses.sqlite")
    output_dir: Path = Path("results/smoke")


def load_config(path: Path) -> RunConfig:
    """Load and validate a UTF-8 YAML config."""
    return RunConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
