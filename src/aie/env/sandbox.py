"""Mocked environment: fake inbox, files and web store. No real I/O ever happens here."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

from aie.models.base import ToolCall


class Email(BaseModel):
    """A fake email. ``date`` is a fixed ISO string (no wall clock)."""

    id: str
    sender: str
    to: list[str]
    subject: str
    body: str
    date: str


class WebDoc(BaseModel):
    """A document in the fake web / RAG store."""

    url: str
    title: str
    content: str


class Action(BaseModel):
    """One logged tool execution. The judge reads these."""

    step: int
    tool: str
    args: dict[str, Any]
    ok: bool
    result: str


class SandboxState(BaseModel):
    """Initial contents of the sandbox."""

    user_email: str
    inbox: list[Email] = Field(default_factory=list)
    files: dict[str, str] = Field(default_factory=dict)
    web: list[WebDoc] = Field(default_factory=list)


def load_state(path: Path) -> SandboxState:
    """Load the initial sandbox state from a UTF-8 YAML fixture."""
    return SandboxState.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


class Sandbox:
    """Holds mutable sandbox state and logs every tool call."""

    def __init__(self, state: SandboxState) -> None:
        self.state = state.model_copy(deep=True)
        self.log: list[Action] = []
        self.outbox: list[Email] = []

    @classmethod
    def from_yaml(cls, path: Path) -> Sandbox:
        """Load a sandbox fixture from a UTF-8 YAML file."""
        return cls(load_state(path))

    def execute(self, call: ToolCall) -> str:
        """Validate and run a tool call, log it, and return the result text.

        Unknown tools, bad arguments and tool errors are logged with ``ok=False`` and returned
        to the agent as text; this method does not raise for them.
        """
        from aie.env.tools import TOOLS, ToolError

        tool = TOOLS.get(call.name)
        if tool is None:
            return self._record(call, False, f"Error: unknown tool {call.name!r}")
        try:
            args = tool.args_model.model_validate(call.arguments)
        except ValidationError as exc:
            return self._record(call, False, f"Error: invalid arguments: {exc.errors()!r}")
        try:
            result = tool.fn(self, **args.model_dump())
        except ToolError as exc:
            return self._record(call, False, f"Error: {exc}")
        return self._record(call, True, result)

    def _record(self, call: ToolCall, ok: bool, result: str) -> str:
        self.log.append(
            Action(
                step=len(self.log), tool=call.name, args=dict(call.arguments), ok=ok, result=result
            )
        )
        return result
