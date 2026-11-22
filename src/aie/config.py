"""Experiment config loaded from ``configs/*.yaml``. Nothing about a run is hardcoded in code."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from aie.defenses.base import DefenseConfig
from aie.models.base import GenConfig, ModelConfig
from aie.scenarios.schema import Channel, Language


def _default_languages() -> list[Language]:
    return ["en"]


def _default_channels() -> list[Channel]:
    return ["email"]


class ExperimentConfig(BaseModel):
    """One experiment: models x (benign + attack x language x channel) over a task library.

    Paths are relative to the working directory, so run from the repository root.
    ``attack_ids: []`` means no attacks (benign only); ``null`` means every attack in the file.
    """

    model_config = ConfigDict(extra="forbid")

    models: list[ModelConfig] = Field(min_length=1)
    defenses: list[DefenseConfig] = Field(default_factory=lambda: [DefenseConfig()], min_length=1)
    gen: GenConfig = Field(default_factory=GenConfig)
    tasks_file: Path = Path("src/aie/scenarios/tasks.yaml")
    attacks_file: Path = Path("src/aie/scenarios/attacks.yaml")
    task_ids: list[str] | None = None
    attack_ids: list[str] | None = None
    languages: list[Language] = Field(default_factory=_default_languages)
    channels: list[Channel] = Field(default_factory=_default_channels)
    include_benign: bool = True
    max_steps: int = 8
    cache_path: Path = Path(".cache/responses.sqlite")
    output_dir: Path = Path("results/runs")


def load_config(path: Path) -> ExperimentConfig:
    """Load and validate a UTF-8 YAML experiment config."""
    return ExperimentConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
