"""Invariants every shipped task must satisfy; they guard the validity of the whole benchmark."""

from pathlib import Path

import pytest

from aie.env.sandbox import Sandbox, SandboxState, load_state
from aie.env.tools import TOOLS
from aie.models.base import ToolCall
from aie.scenarios.build import build_scenario
from aie.scenarios.schema import AnswerContainsAnyCheck, Task, load_attacks, load_tasks, normalize

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _repo_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(REPO)


def tasks() -> list[Task]:
    return load_tasks(REPO / "src/aie/scenarios/tasks.yaml")


def answers(task: Task) -> list[str]:
    (check,) = (c for c in task.utility if isinstance(c, AnswerContainsAnyCheck))
    return check.values


def carrier(task: Task) -> str:
    return task.id.rsplit("__", 1)[1]


def item_body_and_labels(task: Task, state: SandboxState) -> tuple[str, list[str]]:
    """The text of the injected item, and the labels visible WITHOUT opening it."""
    kind = carrier(task)
    if kind == "email":
        e = next(e for e in state.inbox if e.id == task.injection_points["email"])
        return e.body, [e.subject, e.sender, e.id]
    if kind == "file":
        path = task.injection_points["file"]
        return state.files[path], [path]
    d = next(d for d in state.web if d.url == task.injection_points["doc"])
    return d.content, [d.url, d.title]


def test_thirty_unique_tasks_ten_per_carrier() -> None:
    ts = tasks()
    assert len(ts) == 30 and len({t.id for t in ts}) == 30
    assert [sum(carrier(t) == k for t in ts) for k in ("email", "file", "doc")] == [10, 10, 10]


@pytest.mark.parametrize("task", tasks(), ids=lambda t: t.id)
def test_answer_is_only_in_the_body_never_in_visible_labels(task: Task) -> None:
    body, labels = item_body_and_labels(task, load_state(task.fixture))
    for value in answers(task):
        if normalize(value) in normalize(body):
            break
    else:
        pytest.fail(f"{task.id}: no answer value appears in the injected item")
    for value in answers(task):
        for label in labels:
            assert normalize(value) not in normalize(label), f"{task.id}: {value!r} in {label!r}"


@pytest.mark.parametrize("task", tasks(), ids=lambda t: t.id)
def test_answer_is_unambiguous_within_the_fixture(task: Task) -> None:
    state = load_state(task.fixture)
    texts = (
        [e.body for e in state.inbox] + list(state.files.values()) + [d.content for d in state.web]
    )
    key = normalize(answers(task)[0])
    assert sum(key in normalize(t) for t in texts) == 1, f"{task.id}: answer appears in many items"


@pytest.mark.parametrize("task", tasks(), ids=lambda t: t.id)
def test_every_tool_is_offered_so_the_attack_is_possible(task: Task) -> None:
    offered = set(TOOLS) if task.tools is None else set(task.tools)
    assert "send_email" in offered


@pytest.mark.parametrize("task", tasks(), ids=lambda t: t.id)
def test_benign_scenario_contains_no_attacker_text(task: Task) -> None:
    state = build_scenario(task).state
    dump = state.model_dump_json()
    assert "attacker@evil.test" not in dump and "evil.test" not in dump


def test_every_attack_has_all_five_languages_with_the_attacker_address() -> None:
    attacks = load_attacks(REPO / "src/aie/scenarios/attacks.yaml")
    for attack in attacks:
        assert set(attack.payloads) == {"en", "ne", "ne_rom", "hi", "mix"}, attack.id
        assert len({p for p in attack.payloads.values()}) == 5  # no accidental copy-paste
        for lang, text in attack.payloads.items():
            assert attack.goal.to in text, (attack.id, lang)


def test_every_attack_builds_in_every_channel_the_task_supports() -> None:
    attacks = load_attacks(REPO / "src/aie/scenarios/attacks.yaml")
    assert len(attacks) == 3
    built = 0
    for task in tasks():
        for attack in attacks:
            for channel in task.injection_points:
                sc = build_scenario(task, attack, "en", channel)
                payload = attack.payloads["en"]
                if channel == "tool_output":
                    assert sc.tool_output_payloads == {"list_emails": payload}
                else:
                    body, _ = item_body_and_labels(task, sc.state)
                    assert body.endswith(payload)
                built += 1
    assert built == 3 * (20 + 10 + 10)


def model_view(task: Task, channel: str) -> list[tuple[str, str]]:
    """Every (tool, text-as-the-model-sees-it) a perfect agent gets for this task and channel."""
    attack = load_attacks(REPO / "src/aie/scenarios/attacks.yaml")[0]
    sc = build_scenario(task, attack, "en", channel)  # type: ignore[arg-type]
    sb = Sandbox(sc.state)
    calls = [ToolCall(id="c0", name="list_emails", arguments={})]
    calls.append(
        ToolCall(id="c1", name="read_email", arguments={"email_id": task.injection_points["email"]})
    )
    return [(c.name, sc.wrap_tool_output(c.name, sb.execute(c))) for c in calls]


def test_channels_show_the_model_different_text() -> None:
    """Regression: tool_output once duplicated email (byte-identical in 30/30 pairs)."""
    for task in tasks():
        if carrier(task) != "email":
            continue
        email_view = model_view(task, "email")
        tool_view = model_view(task, "tool_output")
        assert email_view != tool_view, task.id
        payload = load_attacks(REPO / "src/aie/scenarios/attacks.yaml")[0].payloads["en"]
        # email channel: the payload is inside the opened email; tool_output: only in the listing.
        assert payload in email_view[1][1] and payload not in email_view[0][1]
        assert payload in tool_view[0][1] and payload not in tool_view[1][1]
