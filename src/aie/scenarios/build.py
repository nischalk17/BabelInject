"""Turn (task, attack, language, channel) into a runnable scenario with the payload placed."""

from __future__ import annotations

from aie.env.sandbox import SandboxState, load_state
from aie.scenarios.schema import Attack, Channel, Language, Scenario, Task


def _append(text: str, payload: str) -> str:
    return f"{text}\n\n{payload}"


def _inject(state: SandboxState, channel: Channel, point: str, payload: str) -> None:
    """Place ``payload`` into ``state`` for the state-based channels (email, file, doc)."""
    if channel == "email":
        for email in state.inbox:
            if email.id == point:
                email.body = _append(email.body, payload)
                return
        raise ValueError(f"injection point: no email with id {point!r}")
    if channel == "file":
        if point not in state.files:
            raise ValueError(f"injection point: no file {point!r}")
        state.files[point] = _append(state.files[point], payload)
        return
    if channel == "doc":
        for doc in state.web:
            if doc.url == point:
                doc.content = _append(doc.content, payload)
                return
        raise ValueError(f"injection point: no web document {point!r}")
    raise ValueError(f"channel {channel!r} is not state-based")


def build_scenario(
    task: Task,
    attack: Attack | None = None,
    language: Language | None = None,
    channel: Channel | None = None,
) -> Scenario:
    """Build a benign scenario (no attack) or an attacked one (attack, language and channel).

    Raises ``ValueError`` if the attack lacks a payload in ``language`` or the task has no
    injection point for ``channel``; nothing is silently skipped.
    """
    state = load_state(task.fixture)
    if attack is None:
        if language is not None or channel is not None:
            raise ValueError("language and channel require an attack")
        return Scenario(id=f"{task.id}|benign", task=task, state=state)
    if language is None or channel is None:
        raise ValueError("an attack needs both language and channel")
    payload = attack.payloads.get(language)
    if payload is None:
        raise ValueError(f"attack {attack.id!r} has no {language!r} payload")
    point = task.injection_points.get(channel)
    if point is None:
        raise ValueError(f"task {task.id!r} has no injection point for channel {channel!r}")
    tool_payloads: dict[str, str] = {}
    if channel == "user":
        # Capability control: the user asks for it directly, so any failure to act is a
        # comprehension limit of the model, not resistance to an injection.
        task = task.model_copy(update={"prompt": payload})
    elif channel == "tool_output":
        tool_payloads[point] = payload
    else:
        _inject(state, channel, point, payload)
    return Scenario(
        id=f"{task.id}|{attack.id}|{language}|{channel}",
        task=task,
        attack=attack,
        language=language,
        channel=channel,
        state=state,
        tool_output_payloads=tool_payloads,
    )
