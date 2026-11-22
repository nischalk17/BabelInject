"""Pluggable defenses. Use ``build_defense`` to create one from a ``DefenseConfig``."""

from __future__ import annotations

from aie.defenses.base import Defense, DefenseConfig, DefenseContext
from aie.defenses.detector import Detector
from aie.defenses.none import NoDefense
from aie.defenses.sandwich import Sandwich
from aie.defenses.spotlight import Spotlight
from aie.defenses.tool_policy import ToolPolicy

__all__ = ["Defense", "DefenseConfig", "DefenseContext", "build_defense"]


def build_defense(cfg: DefenseConfig, ctx: DefenseContext) -> Defense:
    """Create a fresh defense instance (defenses keep per-run event logs, so never share them)."""
    if cfg.name == "none":
        return NoDefense()
    if cfg.name == "spotlight":
        return Spotlight()
    if cfg.name == "sandwich":
        return Sandwich(ctx.task)
    if cfg.name == "tool_policy":
        return ToolPolicy(ctx.state)
    if cfg.name == "detector":
        return Detector(ctx)
    raise ValueError(f"unknown defense {cfg.name!r}")  # pragma: no cover
