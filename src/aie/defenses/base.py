"""Defense interface. A defense can change the system prompt, the tool output the model sees, and
which tool calls are allowed. Everything it does is recorded in ``events`` for later audit."""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict

from aie.env.sandbox import SandboxState
from aie.models.base import GenConfig, ModelAdapter, ModelConfig, ToolCall


class DefenseConfig(BaseModel):
    """Which defense to apply (from the YAML). ``detector_model`` defaults to the agent model."""

    model_config = ConfigDict(extra="forbid")

    name: Literal["none", "spotlight", "sandwich", "tool_policy", "detector"] = "none"
    detector_model: ModelConfig | None = None


@dataclass(frozen=True)
class DefenseContext:
    """What a defense may know about the run it protects."""

    task: str
    state: SandboxState
    detector_model: ModelAdapter
    gen: GenConfig


class Defense(ABC):
    """Base class: every hook does nothing by default. Bump ``version`` before changing any text."""

    name: ClassVar[str]
    version: ClassVar[str]

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def system_prompt(self, base: str) -> str:
        """Return the system prompt to use."""
        return base

    def wrap_tool_output(self, tool_name: str, output: str) -> str:
        """Return what the model should see for a tool result."""
        return output

    def authorize(self, call: ToolCall) -> str | None:
        """Return None to allow the call, or a reason to block it."""
        return None
