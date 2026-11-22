"""Ollama adapter using native tool calling (``/api/chat``)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import httpx

from aie.models.base import (
    GenConfig,
    Message,
    ModelAdapter,
    ModelResponse,
    ToolCall,
    ToolSpec,
)


class OllamaError(RuntimeError):
    """Raised when the Ollama server is unreachable or returns an error."""


class OllamaAdapter(ModelAdapter):
    """Talks to a local Ollama server. Tool calls come from the API's native field only."""

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        client: httpx.Client | None = None,
    ) -> None:
        self._model = model
        self._client = client or httpx.Client(base_url=base_url, timeout=600.0)
        self._tag: str | None = None

    @property
    def model_tag(self) -> str:
        """``ollama/<name>@<first 12 chars of weights digest>``, looked up once."""
        if self._tag is None:
            try:
                resp = self._client.get("/api/tags")
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise OllamaError(f"cannot reach Ollama: {exc}") from exc
            for entry in resp.json().get("models", []):
                if entry.get("name") == self._model:
                    self._tag = f"ollama/{self._model}@{str(entry['digest'])[:12]}"
                    break
            else:
                raise OllamaError(f"model {self._model!r} is not pulled in Ollama")
        return self._tag

    def chat(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        cfg: GenConfig,
    ) -> ModelResponse:
        """Send one non-streaming chat request and parse the reply."""
        body: dict[str, Any] = {
            "model": self._model,
            "messages": [_to_ollama_message(m) for m in messages],
            "stream": False,
            "options": {
                "temperature": cfg.temperature,
                "seed": cfg.seed,
                "num_predict": cfg.max_tokens,
                "num_ctx": cfg.num_ctx,
            },
        }
        if tools:
            body["tools"] = [{"type": "function", "function": t.model_dump()} for t in tools]
        tag = self.model_tag
        try:
            resp = self._client.post("/api/chat", json=body)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise OllamaError(f"Ollama chat request failed: {exc}") from exc
        data: dict[str, Any] = resp.json()
        step = sum(1 for m in messages if m.role == "assistant")
        return ModelResponse(message=_parse_message(data["message"], step), model_tag=tag, raw=data)


def _to_ollama_message(m: Message) -> dict[str, Any]:
    out: dict[str, Any] = {"role": m.role, "content": m.content}
    if m.tool_calls:
        out["tool_calls"] = [
            {"function": {"name": tc.name, "arguments": tc.arguments}} for tc in m.tool_calls
        ]
    return out


def _parse_message(raw: dict[str, Any], step: int) -> Message:
    calls: list[ToolCall] = []
    for i, tc in enumerate(raw.get("tool_calls") or []):
        fn = tc["function"]
        args = fn.get("arguments") or {}
        if isinstance(args, str):
            args = json.loads(args)
        calls.append(ToolCall(id=f"call_{step}_{i}", name=fn["name"], arguments=args))
    return Message(role="assistant", content=raw.get("content") or "", tool_calls=calls)
