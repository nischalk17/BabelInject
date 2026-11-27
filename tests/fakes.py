"""Test doubles. No test touches a real model."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from aie.models.base import GenConfig, Message, ModelAdapter, ModelResponse, ToolSpec


class ScriptedModel(ModelAdapter):
    """Returns pre-scripted assistant messages in order and counts calls."""

    def __init__(
        self,
        responses: list[Message],
        tag: str = "fake/scripted@0",
        raws: list[dict[str, Any]] | None = None,
    ) -> None:
        self._responses = list(responses)
        self._raws = raws or []
        self._tag = tag
        self.calls = 0
        self.seen: list[list[Message]] = []

    @property
    def model_tag(self) -> str:
        return self._tag

    def chat(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        cfg: GenConfig,
    ) -> ModelResponse:
        self.seen.append(list(messages))
        msg = self._responses[self.calls]
        self.calls += 1
        raw = self._raws[self.calls - 1] if self.calls <= len(self._raws) else {}
        return ModelResponse(message=msg, model_tag=self._tag, raw=raw)
