"""ReAct-style agent loop: model call -> tool calls -> observations, until a final answer."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Literal

from pydantic import BaseModel

from aie.agent.prompts import PROMPT_VERSION, SYSTEM_PROMPT
from aie.env.sandbox import Action, Sandbox
from aie.env.tools import tool_specs
from aie.models.base import GenConfig, Message, ModelAdapter, ToolCall


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
    system_prompt: str = SYSTEM_PROMPT,
    authorize: Callable[[ToolCall], str | None] | None = None,
) -> AgentResult:
    """Run the agent on ``task`` until it answers without tool calls or hits ``max_steps``.

    Hooks used by defenses (all optional, all default to "no defense"):

    - ``wrap_tool_output(tool_name, output)`` is applied to every observation before the model sees
      it. The sandbox log keeps the raw, unwrapped result.
    - ``system_prompt`` replaces the system prompt. ``PROMPT_VERSION`` describes the default text,
      so a changed prompt is identified by the defense name and version instead.
    - ``authorize(call)`` returns None to allow a call, or a reason string to block it. A blocked
      call is logged as a failed action and the reason is shown to the model.

    A call to a tool that was not offered to the model is always rejected, never executed.
    """
    cfg = cfg or GenConfig()
    specs = tool_specs(tools)
    offered = {s.name for s in specs}
    messages = [
        Message(role="system", content=system_prompt),
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
            blocked = None if authorize is None else authorize(call)
            if call.name not in offered:
                out = sandbox.reject(call, f"Error: tool {call.name!r} is not available")
            elif blocked is not None:
                out = sandbox.reject(call, blocked)
            else:
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
