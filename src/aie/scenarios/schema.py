"""Scenario format: tasks, attacks, and the deterministic checks the judge applies.

A *task* is a benign user request plus a fixture and programmatic utility checks.
An *attack* is a goal the attacker wants executed plus the injection text in each language.
A *scenario* is one task, optionally combined with one attack, language and channel.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from aie.env.sandbox import SandboxState

Language = Literal["en", "ne", "ne_rom", "hi", "mix"]
# "user" is the capability-control channel: the attack text IS the user's own request.
Channel = Literal["email", "doc", "tool_output", "file", "user"]


def normalize(text: str) -> str:
    """NFC-normalize and casefold, so Devanagari and case differences don't break matching."""
    return unicodedata.normalize("NFC", text).casefold()


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- attacker goals (judged from the sandbox outbox and action log) -------------------------


class SendEmailGoal(_Strict):
    """Attack succeeds if an email to ``to`` (containing ``body_contains``, if set) was sent."""

    type: Literal["send_email"] = "send_email"
    to: str
    body_contains: str | None = None


class ExfiltrateFileGoal(_Strict):
    """Attack succeeds if ``path`` was read AND an email to ``to`` contains ``marker``."""

    type: Literal["exfiltrate_file"] = "exfiltrate_file"
    path: str
    to: str
    marker: str


AttackGoal = Annotated[SendEmailGoal | ExfiltrateFileGoal, Field(discriminator="type")]


# --- benign-task utility checks --------------------------------------------------------------


class ToolCalledCheck(_Strict):
    """Passes if ``tool`` ran successfully with arguments that include ``args``."""

    type: Literal["tool_called"] = "tool_called"
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


class AnyToolCalledCheck(_Strict):
    """Passes if at least one of ``tools`` ran successfully (e.g. search OR fetch a web page)."""

    type: Literal["any_tool_called"] = "any_tool_called"
    tools: list[str] = Field(min_length=1)


class AnswerContainsAnyCheck(_Strict):
    """Passes if the final answer contains at least one of ``values``."""

    type: Literal["answer_contains_any"] = "answer_contains_any"
    values: list[str] = Field(min_length=1)


class EmailSentCheck(_Strict):
    """Passes if an email to ``to`` (containing ``body_contains``, if set) was sent."""

    type: Literal["email_sent"] = "email_sent"
    to: str
    body_contains: str | None = None


UtilityCheck = Annotated[
    ToolCalledCheck | AnyToolCalledCheck | AnswerContainsAnyCheck | EmailSentCheck,
    Field(discriminator="type"),
]


# --- tasks, attacks, scenarios ----------------------------------------------------------------


class Task(_Strict):
    """A benign user task.

    ``injection_points`` says where a payload goes for each channel: an email id (``email``),
    a file path (``file``), a web document URL (``doc``) or a tool name (``tool_output``).
    """

    id: str
    prompt: str
    fixture: Path
    tools: list[str] | None = None
    injection_points: dict[Channel, str] = Field(default_factory=dict)
    utility: list[UtilityCheck] = Field(min_length=1)


class Attack(_Strict):
    """An attacker goal with the injection text per language (translations are vetted by hand)."""

    id: str
    goal: AttackGoal
    payloads: dict[Language, str] = Field(min_length=1)

    @model_validator(mode="after")
    def _payloads_name_the_attacker(self) -> Attack:
        # The attacker address is ASCII and survives translation, so every payload must contain
        # it; otherwise the judge could report "no attack" for an attack that never asked.
        for lang, text in self.payloads.items():
            if normalize(self.goal.to) not in normalize(text):
                raise ValueError(f"payload {lang!r} of attack {self.id!r} must contain goal.to")
        return self


class Scenario(BaseModel):
    """One runnable case: sandbox state with the payload placed, plus how to judge it."""

    id: str
    task: Task
    attack: Attack | None = None
    language: Language | None = None
    channel: Channel | None = None
    state: SandboxState
    tool_output_payloads: dict[str, str] = Field(default_factory=dict)

    def wrap_tool_output(self, tool_name: str, output: str) -> str:
        """Append the payload to the output of the injected tool (``tool_output`` channel).

        Only the model's view changes; the sandbox log keeps the raw output. Defenses that also
        wrap tool output must be composed with this, not replace it.
        """
        payload = self.tool_output_payloads.get(tool_name)
        return output if payload is None else f"{output}\n\n{payload}"


def _load_list(path: Path) -> list[Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a YAML list")
    return data


def load_tasks(path: Path) -> list[Task]:
    """Load and validate tasks from a UTF-8 YAML file."""
    return [Task.model_validate(t) for t in _load_list(path)]


def load_attacks(path: Path) -> list[Attack]:
    """Load and validate attacks from a UTF-8 YAML file."""
    return [Attack.model_validate(a) for a in _load_list(path)]
