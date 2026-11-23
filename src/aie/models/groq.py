"""Groq adapter (OpenAI-compatible chat completions with tool calling).

The API key comes from ``GROQ_API_KEY`` (environment or ``.env``) and is only ever sent in the
Authorization header; it is never logged, stored in results or included in error messages.
Hosted models can change silently, so the response's returned model id and fingerprint are kept in
``ModelResponse.raw`` and every row should be read together with its run date.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
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
from aie.secrets import get_secret

DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
RETRYABLE = {429, 500, 502, 503, 504}
# The free tier refills a daily token quota continuously, so after a stop each call waits for its
# own tokens. For that case (and only that) we wait as long as Groq says, up to this cap per wait.
QUOTA_WAIT_CAP_S = 1200.0
QUOTA_WAIT_MARGIN_S = 5.0


class GroqError(RuntimeError):
    """Raised for a missing key, HTTP errors or exhausted retries. Never contains the key."""


class GroqAdapter(ModelAdapter):
    """Talks to Groq's hosted models."""

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        max_retries: int = 5,
        max_quota_waits: int = 100,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        key = api_key or get_secret("GROQ_API_KEY")
        if not key:
            raise GroqError("GROQ_API_KEY is not set (put it in the environment or in .env)")
        self._model = model
        self._key = key
        self._client = client or httpx.Client(base_url=base_url or DEFAULT_BASE_URL, timeout=120.0)
        self._max_retries = max_retries
        self._max_quota_waits = max_quota_waits
        self._sleep = sleep

    def __repr__(self) -> str:
        return f"GroqAdapter(model={self._model!r})"  # never include the key

    @property
    def model_tag(self) -> str:
        """``groq/<configured model name>``; the returned model id is kept in ``raw``."""
        return f"groq/{self._model}"

    def chat(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        cfg: GenConfig,
    ) -> ModelResponse:
        """Send one non-streaming request, retrying rate limits and transient server errors."""
        body: dict[str, Any] = {
            "model": self._model,
            "messages": [_to_openai_message(m) for m in messages],
            "temperature": cfg.temperature,
            "seed": cfg.seed,
            "max_tokens": cfg.max_tokens,
        }
        if tools:
            body["tools"] = [{"type": "function", "function": t.model_dump()} for t in tools]
        headers = {"Authorization": f"Bearer {self._key}"}
        quota_waits = 0
        attempt = 0
        while attempt <= self._max_retries:
            try:
                resp = self._client.post("/chat/completions", json=body, headers=headers)
            except httpx.TransportError as exc:
                if attempt == self._max_retries:
                    raise GroqError(f"Groq request failed: {type(exc).__name__}") from exc
                self._sleep(_backoff(attempt, None))
                attempt += 1
                continue
            if (
                resp.status_code == 429
                and _is_daily_token_limit(resp)
                and quota_waits < self._max_quota_waits
            ):
                quota_waits += 1  # does not use up the normal retries
                self._sleep(_quota_wait(resp.headers.get("retry-after")))
                continue
            if resp.status_code in RETRYABLE and attempt < self._max_retries:
                self._sleep(_backoff(attempt, resp.headers.get("retry-after")))
                attempt += 1
                continue
            if resp.status_code != 200:
                raise GroqError(f"Groq returned HTTP {resp.status_code}: {_error_text(resp)}")
            data: dict[str, Any] = resp.json()
            return ModelResponse(
                message=_parse_message(data["choices"][0]["message"]),
                model_tag=self.model_tag,
                raw={
                    "returned_model": data.get("model"),
                    "system_fingerprint": data.get("system_fingerprint"),
                    "usage": data.get("usage"),
                },
            )
        raise GroqError("Groq retries exhausted")  # pragma: no cover


def _backoff(attempt: int, retry_after: str | None) -> float:
    if retry_after:
        try:
            return min(float(retry_after), 60.0)
        except ValueError:
            pass
    return float(min(2**attempt, 30))


def _is_daily_token_limit(resp: httpx.Response) -> bool:
    return "tokens per day" in _error_text(resp).lower()


def _quota_wait(retry_after: str | None) -> float:
    try:
        wait = float(retry_after) if retry_after else QUOTA_WAIT_CAP_S
    except ValueError:
        wait = QUOTA_WAIT_CAP_S
    return min(wait, QUOTA_WAIT_CAP_S) + QUOTA_WAIT_MARGIN_S


def _error_text(resp: httpx.Response) -> str:
    try:
        return str(resp.json().get("error", {}).get("message", ""))[:300]
    except ValueError:
        return resp.text[:300]


def _to_openai_message(m: Message) -> dict[str, Any]:
    out: dict[str, Any] = {"role": m.role, "content": m.content}
    if m.tool_calls:
        out["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
            }
            for tc in m.tool_calls
        ]
    if m.role == "tool" and m.tool_call_id:
        out["tool_call_id"] = m.tool_call_id
    return out


def _parse_message(raw: dict[str, Any]) -> Message:
    calls: list[ToolCall] = []
    for tc in raw.get("tool_calls") or []:
        fn = tc["function"]
        args: Any = fn.get("arguments") or "{}"
        try:
            parsed = json.loads(args) if isinstance(args, str) else args
        except json.JSONDecodeError:
            parsed = {"_unparsed_arguments": args}  # surfaces as a logged bad-arguments failure
        if not isinstance(parsed, dict):
            parsed = {"_unparsed_arguments": args}
        calls.append(ToolCall(id=tc["id"], name=fn["name"], arguments=parsed))
    return Message(role="assistant", content=raw.get("content") or "", tool_calls=calls)
