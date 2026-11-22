"""Provider-neutral message, tool and model-adapter types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    """A tool the model may call; ``parameters`` is a JSON Schema object."""

    name: str
    description: str
    parameters: dict[str, Any]


class ToolCall(BaseModel):
    """A single tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]


class Message(BaseModel):
    """One chat message. ``tool`` messages carry a tool result."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None


class GenConfig(BaseModel):
    """Generation settings. Temperature 0 by default (see CLAUDE.md)."""

    temperature: float = 0.0
    seed: int = 0
    max_tokens: int = 1024
    num_ctx: int = 8192


class ModelConfig(BaseModel):
    """Which model to run; comes from ``configs/*.yaml``."""

    provider: Literal["ollama", "groq"] = "ollama"
    model: str
    base_url: str | None = None  # None = the provider's default


class ModelResponse(BaseModel):
    """A model reply plus the exact model tag that produced it."""

    message: Message
    model_tag: str
    cached: bool = False
    raw: dict[str, Any] = Field(default_factory=dict)


class ModelAdapter(ABC):
    """Interface every model backend implements."""

    @property
    @abstractmethod
    def model_tag(self) -> str:
        """Exact model identifier, e.g. ``ollama/qwen2.5:3b@357c53fb659c``."""

    @abstractmethod
    def chat(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        cfg: GenConfig,
    ) -> ModelResponse:
        """Return the model's next message for the conversation."""
