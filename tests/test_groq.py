import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from aie.models.base import GenConfig, Message, ModelConfig, ToolCall, ToolSpec
from aie.models.cache import CachedModel, build_model
from aie.models.groq import GroqAdapter, GroqError

KEY = "gsk_TESTKEY_do_not_leak"
TOOLS = [ToolSpec(name="read_email", description="d", parameters={"type": "object"})]


def adapter(handler: Any, sleeps: list[float] | None = None, max_retries: int = 5) -> GroqAdapter:
    client = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
    return GroqAdapter(
        "llama-test",
        api_key=KEY,
        client=client,
        max_retries=max_retries,
        sleep=(sleeps.append if sleeps is not None else lambda s: None),
    )


def ok(message: dict[str, Any]) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": "llama-test-0611",
            "system_fingerprint": "fp_1",
            "choices": [{"message": message}],
        },
    )


def test_request_shape_tool_calls_and_raw_metadata() -> None:
    seen: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return ok(
            {
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_abc",
                        "type": "function",
                        "function": {"name": "read_email", "arguments": '{"email_id": "e1"}'},
                    }
                ],
            }
        )

    history = [
        Message(role="user", content="hi"),
        Message(role="assistant", tool_calls=[ToolCall(id="c0", name="list_emails", arguments={})]),
        Message(role="tool", content="e1 | ...", tool_call_id="c0"),
    ]
    resp = adapter(handler).chat(history, TOOLS, GenConfig(seed=7))

    req = seen[0]
    body = json.loads(req.content)
    assert req.url.path == "/chat/completions"
    assert req.headers["authorization"] == f"Bearer {KEY}"
    assert (body["temperature"], body["seed"], body["max_tokens"]) == (0.0, 7, 1024)
    assert body["tools"][0]["function"]["name"] == "read_email"
    assert body["messages"][1]["tool_calls"][0]["function"]["arguments"] == "{}"
    assert body["messages"][2] == {"role": "tool", "content": "e1 | ...", "tool_call_id": "c0"}
    assert resp.message.tool_calls == [
        ToolCall(id="call_abc", name="read_email", arguments={"email_id": "e1"})
    ]
    assert resp.model_tag == "groq/llama-test"
    assert resp.raw["returned_model"] == "llama-test-0611"
    assert resp.raw["system_fingerprint"] == "fp_1"
    assert KEY not in resp.model_dump_json()


def test_malformed_tool_arguments_surface_instead_of_crashing() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return ok(
            {
                "content": "",
                "tool_calls": [
                    {
                        "id": "c",
                        "type": "function",
                        "function": {"name": "read_email", "arguments": "{oops"},
                    }
                ],
            }
        )

    call = adapter(handler).chat([Message(role="user", content="x")], TOOLS, GenConfig())
    assert call.message.tool_calls[0].arguments == {"_unparsed_arguments": "{oops"}


def test_rate_limit_is_retried_with_retry_after() -> None:
    replies = [
        httpx.Response(429, headers={"retry-after": "3"}, json={"error": {"message": "slow"}}),
        httpx.Response(503, json={}),
        ok({"content": "done"}),
    ]
    sleeps: list[float] = []
    a = adapter(lambda req: replies.pop(0), sleeps)
    resp = a.chat([Message(role="user", content="x")], [], GenConfig())
    assert resp.message.content == "done"
    assert sleeps == [3.0, 2.0]  # retry-after honored, then exponential backoff (2**1)


def test_retries_are_bounded() -> None:
    sleeps: list[float] = []
    a = adapter(lambda req: httpx.Response(429, json={}), sleeps, max_retries=2)
    with pytest.raises(GroqError, match="HTTP 429"):
        a.chat([Message(role="user", content="x")], [], GenConfig())
    assert len(sleeps) == 2


def test_client_errors_are_not_retried_and_never_leak_the_key() -> None:
    calls: list[int] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(401, json={"error": {"message": "invalid api key"}})

    with pytest.raises(GroqError) as err:
        adapter(handler).chat([Message(role="user", content="x")], [], GenConfig())
    assert len(calls) == 1
    assert "401" in str(err.value) and KEY not in str(err.value)
    assert KEY not in repr(adapter(handler))


def test_missing_key_raises_clearly(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)  # no .env here
    with pytest.raises(GroqError, match="GROQ_API_KEY"):
        GroqAdapter("llama-test")


def test_build_model_wraps_groq_in_the_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", KEY)
    model = build_model(ModelConfig(provider="groq", model="llama-test"), tmp_path / "c.sqlite")
    assert isinstance(model, CachedModel)
    assert model.model_tag == "groq/llama-test"
