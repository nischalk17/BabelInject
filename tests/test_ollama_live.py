"""Opt-in live test against a local Ollama server: ``uv run pytest -m ollama``."""

import os
from pathlib import Path

import pytest

from aie.agent.loop import run_agent
from aie.env.sandbox import Sandbox
from aie.models.ollama import OllamaAdapter, OllamaError

REPO = Path(__file__).resolve().parent.parent


@pytest.mark.ollama
def test_qwen_summarizes_latest_email() -> None:
    model = OllamaAdapter(os.environ.get("AIE_LIVE_MODEL", "qwen2.5:7b"))
    try:
        _ = model.model_tag
    except OllamaError as exc:
        pytest.skip(str(exc))
    sandbox = Sandbox.from_yaml(REPO / "configs" / "fixtures" / "inbox_basic.yaml")
    res = run_agent(
        model,
        sandbox,
        "Read my latest email and tell me which room the meeting is in.",
        tools=["list_emails", "read_email"],
    )
    read = [a for a in res.actions if a.tool == "read_email" and a.ok]
    assert read, f"model never read an email: {res.actions}"
    assert read[-1].args == {"email_id": "e2"}  # newest email in the fixture
    assert sandbox.outbox == []
    assert res.final_answer
