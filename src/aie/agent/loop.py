"""ReAct-style agent loop: model call -> tool calls -> observations, until a final answer."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Literal

from pydantic import BaseModel

from aie.agent.prompts import PROMPT_VERSION, SYSTEM_PROMPT
from aie.env.sandbox import Action, Sandbox
from aie.env.tools import tool_specs
from aie.models.base import GenConfig, Message, ModelAdapter


class AgentResult(BaseModel):
    """Everything about one agent run; serializes straight to a JSONL row."""

    final_answer: str | None
    stop_reason: Literal["final", "max_steps"]
    steps: int
    messages: list[Message]
    actions: list[Action]
    model_tag: str
    prompt_version: str


def identity(tool_name: str, output: str) -> str:
    """Default tool-output wrapper: leave the output unchanged."""
    return output


def run_agent(
    model: ModelAdapter,
    sandbox: Sandbox,
    task: str,
    *,
    tools: Sequence[str] | None = None,
    cfg: GenConfig | None = None,
    max_steps: int = 8,
    wrap_tool_output: Callable[[str, str], str] = identity,
) -> AgentResult:
    """Run the agent on ``task`` until it answers without tool calls or hits ``max_steps``.

    ``wrap_tool_output(tool_name, output)`` is applied to every observation before the model
    sees it; this is where output-side defenses (e.g. spotlighting) plug in. The sandbox log
    keeps the raw, unwrapped result.
    """
    cfg = cfg or GenConfig()
    specs = tool_specs(tools)
    messages = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=task),
    ]
    tag = ""
    final: str | None = None
    reason: Literal["final", "max_steps"] = "max_steps"
    steps = 0
    for steps in range(1, max_steps + 1):  # noqa: B007 - steps is read after the loop
        resp = model.chat(messages, specs, cfg)
        tag = resp.model_tag
        messages.append(resp.message)
        if not resp.message.tool_calls:
            final, reason = resp.message.content, "final"
            break
        for call in resp.message.tool_calls:
            out = sandbox.execute(call)
            messages.append(
                Message(
                    role="tool",
                    content=wrap_tool_output(call.name, out),
                    tool_call_id=call.id,
                )
            )
    return AgentResult(
        final_answer=final,
        stop_reason=reason,
        steps=steps,
        messages=messages,
        actions=list(sandbox.log),
        model_tag=tag,
        prompt_version=PROMPT_VERSION,
    )
