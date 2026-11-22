from aie.env.sandbox import Sandbox
from aie.env.tools import TOOLS, tool_specs
from aie.models.base import ToolCall


def run(sb: Sandbox, name: str, **args: object) -> str:
    return sb.execute(ToolCall(id="c", name=name, arguments=dict(args)))


def test_list_emails_newest_first_and_limit(sandbox: Sandbox) -> None:
    lines = run(sandbox, "list_emails").splitlines()
    assert lines[0].startswith("e2 |") and lines[1].startswith("e1 |")
    assert run(sandbox, "list_emails", limit=1).count("\n") == 0


def test_read_email_includes_headers_and_body(sandbox: Sandbox) -> None:
    out = run(sandbox, "read_email", email_id="e2")
    assert "From: b@example.test" in out and "Subject: Newest" in out and "newest body" in out


def test_files(sandbox: Sandbox) -> None:
    assert run(sandbox, "list_files").splitlines() == ["notes.txt", "plan.md"]
    assert run(sandbox, "read_file", path="notes.txt") == "private notes"
    assert "no such file" in run(sandbox, "read_file", path="nope")


def test_search_web_is_deterministic_and_ranked(sandbox: Sandbox) -> None:
    first = run(sandbox, "search_web", query="sleep")
    assert first == run(sandbox, "search_web", query="sleep")
    assert first.index("w.test/1") < first.index("w.test/3")  # tie -> store order
    assert "w.test/2" not in first
    assert run(sandbox, "search_web", query="zzz") == "No results."


def test_search_web_handles_devanagari(sandbox: Sandbox) -> None:
    out = run(sandbox, "search_web", query="नेपालको राजधानी")
    assert out.startswith("https://w.test/2")


def test_fetch_url(sandbox: Sandbox) -> None:
    assert "cats purr" in run(sandbox, "fetch_url", url="https://w.test/1")
    assert "could not fetch" in run(sandbox, "fetch_url", url="https://nope.test")


def test_tool_specs_cover_registry_and_are_json_schema() -> None:
    specs = {s.name: s for s in tool_specs()}
    assert set(specs) == set(TOOLS)
    assert specs["read_email"].parameters["required"] == ["email_id"]
    assert "title" not in specs["read_email"].parameters
    assert [s.name for s in tool_specs(["send_email"])] == ["send_email"]
