"""Expand an experiment config into the list of scenarios to run."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from pydantic import BaseModel

from aie.config import ExperimentConfig
from aie.scenarios.build import build_scenario
from aie.scenarios.schema import Attack, Scenario, Task


class SkippedCell(BaseModel):
    """A grid cell that was not built because the task has no injection point for the channel."""

    task_id: str
    attack_id: str
    language: str
    channel: str
    reason: str


_T = TypeVar("_T", Task, Attack)


def _select(items: Sequence[_T], ids: list[str] | None, kind: str) -> list[_T]:
    if ids is None:
        return list(items)
    by_id = {i.id: i for i in items}
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        raise ValueError(f"unknown {kind} id(s): {unknown}")
    return [by_id[i] for i in ids]


def build_grid(
    cfg: ExperimentConfig, tasks: Sequence[Task], attacks: Sequence[Attack]
) -> tuple[list[Scenario], list[SkippedCell]]:
    """Build every scenario the config asks for, in a deterministic order.

    A task that simply has no injection point for a channel is skipped, and the skip is returned
    so it can be reported. A missing translation (attack has no payload in a requested language)
    is an error: an incomplete grid must never look complete.
    """
    scenarios: list[Scenario] = []
    skipped: list[SkippedCell] = []
    for task in _select(tasks, cfg.task_ids, "task"):
        if cfg.include_benign:
            scenarios.append(build_scenario(task))
        for attack in _select(attacks, cfg.attack_ids, "attack"):
            for language in cfg.languages:
                for channel in cfg.channels:
                    if channel not in task.injection_points:
                        skipped.append(
                            SkippedCell(
                                task_id=task.id,
                                attack_id=attack.id,
                                language=language,
                                channel=channel,
                                reason=f"task has no injection point for channel {channel!r}",
                            )
                        )
                        continue
                    scenarios.append(build_scenario(task, attack, language, channel))
    return scenarios, skipped
