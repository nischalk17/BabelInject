from aie.agent.loop import run_agent
from aie.agent.prompts import PROMPT_VERSION
from aie.env.sandbox import Sandbox
from aie.models.base import Message, ToolCall
from tests.fakes import ScriptedModel


def calling(call_id: str, name: str, **args: object) -> Message:
    return Message(
        role="assistant", tool_calls=[ToolCall(id=call_id, name=name, arguments=dict(args))]
    )


def final(text: str) -> Message:
    return Message(role="assistant", content=text)


def test_summarize_latest_email(sandbox: Sandbox) -> None:
    model = ScriptedModel(
        [
            calling("c0", "list_emails"),
            calling("c1", "read_email", email_id="e2"),
            final("The newest email says: newest body."),
        ]
    )
    res = run_agent(model, sandbox, "Summarize my latest email.")

    assert res.stop_reason == "final"
    assert res.final_answer == "The newest email says: newest body."
    assert res.steps == 3
    assert [a.tool for a in res.actions] == ["list_emails", "read_email"]
    assert res.actions[1].args == {"email_id": "e2"}
    assert res.model_tag == "fake/scripted@0"
    assert res.prompt_version == PROMPT_VERSION
    assert sandbox.outbox == []
    roles = [m.role for m in res.messages]
    assert roles == ["system", "user", "assistant", "tool", "assistant", "tool", "assistant"]
    assert res.messages[3].tool_call_id == "c0"
    assert "newest body" in res.messages[5].content


def test_stops_at_max_steps(sandbox: Sandbox) -> None:
    model = ScriptedModel([calling(f"c{i}", "list_emails") for i in range(5)])
    res = run_agent(model, sandbox, "loop forever", max_steps=3)
    assert res.stop_reason == "max_steps"
    assert res.final_answer is None
    assert res.steps == 3
    assert model.calls == 3


def test_recovers_after_bad_tool_call(sandbox: Sandbox) -> None:
    model = ScriptedModel(
        [
            calling("c0", "read_email", email_id="nope"),
            calling("c1", "read_email", email_id="e2"),
            final("done"),
        ]
    )
    res = run_agent(model, sandbox, "task")
    assert [a.ok for a in res.actions] == [False, True]
    assert "no email" in res.messages[3].content
    assert res.final_answer == "done"


def test_wrap_tool_output_changes_model_view_not_log(sandbox: Sandbox) -> None:
    model = ScriptedModel([calling("c0", "read_email", email_id="e2"), final("ok")])
    res = run_agent(
        model,
        sandbox,
        "task",
        wrap_tool_output=lambda name, out: f"<data tool={name}>{out}</data>",
    )
    assert res.messages[3].content.startswith("<data tool=read_email>")
    assert not res.actions[0].result.startswith("<data")


def test_tools_argument_limits_specs_sent_to_model(sandbox: Sandbox) -> None:
    seen: list[list[str]] = []

    class Spy(ScriptedModel):
        def chat(self, messages, tools, cfg):  # type: ignore[no-untyped-def]
            seen.append([t.name for t in tools])
            return super().chat(messages, tools, cfg)

    run_agent(Spy([final("x")]), sandbox, "task", tools=["list_emails"])
    assert seen == [["list_emails"]]
