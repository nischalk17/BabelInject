import json
from typing import Any

import httpx
import pytest

from aie.models.base import GenConfig, Message, ToolCall, ToolSpec
from aie.models.ollama import OllamaAdapter, OllamaError

TOOLS = [ToolSpec(name="read_email", description="d", parameters={"type": "object"})]
TAGS = {"models": [{"name": "qwen2.5:3b", "digest": "357c53fb659c9999"}]}


def make(reply: dict[str, Any], seen: list[dict[str, Any]], status: int = 200) -> OllamaAdapter:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json=TAGS)
        seen.append(json.loads(request.content))
        return httpx.Response(status, json=reply)

    client = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
    return OllamaAdapter("qwen2.5:3b", client=client)


def test_request_body_and_tool_call_parsing() -> None:
    seen: list[dict[str, Any]] = []
    reply = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "read_email", "arguments": {"email_id": "e1"}}},
                {"function": {"name": "read_email", "arguments": '{"email_id": "e2"}'}},
            ],
        }
    }
    adapter = make(reply, seen)
    history = [Message(role="user", content="hi"), Message(role="assistant", content="ok")]
    resp = adapter.chat(history, TOOLS, GenConfig(seed=3, num_ctx=4096))

    body = seen[0]
    assert body["stream"] is False
    assert body["options"] == {
        "temperature": 0.0,
        "seed": 3,
        "num_predict": 1024,
        "num_ctx": 4096,
    }
    assert body["tools"][0]["function"]["name"] == "read_email"
    assert resp.message.tool_calls == [
        ToolCall(id="call_1_0", name="read_email", arguments={"email_id": "e1"}),
        ToolCall(id="call_1_1", name="read_email", arguments={"email_id": "e2"}),
    ]
    assert resp.model_tag == "ollama/qwen2.5:3b@357c53fb659c"


def test_text_only_reply() -> None:
    seen: list[dict[str, Any]] = []
    adapter = make({"message": {"role": "assistant", "content": "done"}}, seen)
    resp = adapter.chat([Message(role="user", content="hi")], [], GenConfig())
    assert resp.message.content == "done"
    assert resp.message.tool_calls == []
    assert "tools" not in seen[0]


def test_http_error_raises() -> None:
    adapter = make({"error": "boom"}, [], status=500)
    with pytest.raises(OllamaError):
        adapter.chat([Message(role="user", content="hi")], [], GenConfig())


def test_unpulled_model_raises() -> None:
    client = httpx.Client(
        base_url="http://test",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"models": []})),
    )
    with pytest.raises(OllamaError, match="not pulled"):
        _ = OllamaAdapter("qwen2.5:3b", client=client).model_tag


def test_malformed_string_arguments_are_kept_not_raised() -> None:
    reply = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "read_email", "arguments": "{not json"}},
                {"function": {"name": "list_emails", "arguments": "[1, 2]"}},
            ],
        }
    }
    adapter = make(reply, [])
    resp = adapter.chat([Message(role="user", content="hi")], [], GenConfig())
    assert [c.arguments for c in resp.message.tool_calls] == [
        {"_unparsed_arguments": "{not json"},
        {"_unparsed_arguments": [1, 2]},
    ]
