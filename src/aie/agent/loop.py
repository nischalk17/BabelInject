"""ReAct-style agent loop: model call -> tool calls -> observations, until a final answer."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Literal

from pydantic import BaseModel, Field

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
    # Distinct (returned_model, system_fingerprint) pairs the provider reported, so hosted-model
    # drift can be checked from the result rows alone. Empty for local models and older rows.
    served_by: list[dict[str, str | None]] = Field(default_factory=list)
    # Replies cut off by the token limit (finish/done reason "length"); such a step may be a
    # half-written tool call or answer, so a nonzero count is worth a look.
    truncated_steps: int = 0


def identity(tool_name: str, output: str) -> str:
    """Default tool-output wrapper: leave the output unchanged."""
    return output


def _served_by(raw: dict[str, Any]) -> dict[str, str | None]:
    """The provider-reported model id and fingerprint from a response, or {} if it gave none."""
    returned, fingerprint = raw.get("returned_model"), raw.get("system_fingerprint")
    if returned is None and fingerprint is None:
        return {}
    return {
        "returned_model": None if returned is None else str(returned),
        "system_fingerprint": None if fingerprint is None else str(fingerprint),
    }


def _was_truncated(raw: dict[str, Any]) -> bool:
    """True if the provider says the reply stopped at the token limit."""
    return "length" in (raw.get("finish_reason"), raw.get("done_reason"))


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
    served_by: list[dict[str, str | None]] = []
    truncated = 0
    for steps in range(1, max_steps + 1):  # noqa: B007 - steps is read after the loop
        resp = model.chat(messages, specs, cfg)
        tag = resp.model_tag
        truncated += _was_truncated(resp.raw)
        served = _served_by(resp.raw)
        if served and served not in served_by:
            served_by.append(served)
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
        served_by=served_by,
        truncated_steps=truncated,
    )
