from pathlib import Path

from aie.env.sandbox import Sandbox, SandboxState
from aie.models.base import ToolCall


def call(name: str, **args: object) -> ToolCall:
    return ToolCall(id="c", name=name, arguments=dict(args))


def test_every_call_is_logged_in_order(sandbox: Sandbox) -> None:
    sandbox.execute(call("list_emails"))
    sandbox.execute(call("read_email", email_id="e2"))
    assert [(a.step, a.tool, a.ok) for a in sandbox.log] == [
        (0, "list_emails", True),
        (1, "read_email", True),
    ]
    assert sandbox.log[1].args == {"email_id": "e2"}
    assert "newest body" in sandbox.log[1].result


def test_unknown_tool_and_bad_args_are_logged_not_raised(sandbox: Sandbox) -> None:
    assert "unknown tool" in sandbox.execute(call("rm_rf"))
    assert "invalid arguments" in sandbox.execute(call("read_email"))
    assert "invalid arguments" in sandbox.execute(call("read_email", email_id="e1", extra=1))
    assert "no email" in sandbox.execute(call("read_email", email_id="zzz"))
    assert [a.ok for a in sandbox.log] == [False, False, False, False]


def test_send_email_only_fills_outbox(sandbox: Sandbox, state: SandboxState) -> None:
    sandbox.execute(call("send_email", to="x@evil.test", subject="s", body="b"))
    assert [(e.to, e.sender) for e in sandbox.outbox] == [(["x@evil.test"], "me@example.test")]
    assert len(sandbox.state.inbox) == len(state.inbox)
    assert sandbox.log[0].tool == "send_email"


def test_input_state_is_not_mutated(state: SandboxState) -> None:
    before = state.model_dump()
    sb = Sandbox(state)
    sb.execute(call("send_email", to="x@y.test", subject="s", body="b"))
    sb.state.files["new"] = "x"
    assert state.model_dump() == before


def test_from_yaml_reads_utf8(tmp_path: Path) -> None:
    p = tmp_path / "s.yaml"
    p.write_text(
        "user_email: me@example.test\nfiles:\n  a.txt: नमस्ते\n",
        encoding="utf-8",
    )
    sb = Sandbox.from_yaml(p)
    assert sb.state.files["a.txt"] == "नमस्ते"
