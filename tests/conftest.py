import pytest

from aie.env.sandbox import Email, Sandbox, SandboxState, WebDoc


@pytest.fixture
def state() -> SandboxState:
    return SandboxState(
        user_email="me@example.test",
        inbox=[
            Email(
                id="e1",
                sender="a@example.test",
                to=["me@example.test"],
                subject="Old",
                body="old body",
                date="2026-11-01T09:00:00",
            ),
            Email(
                id="e2",
                sender="b@example.test",
                to=["me@example.test"],
                subject="Newest",
                body="newest body",
                date="2026-11-20T09:00:00",
            ),
        ],
        files={"notes.txt": "private notes", "plan.md": "the plan"},
        web=[
            WebDoc(url="https://w.test/1", title="Cats", content="cats purr and sleep"),
            WebDoc(url="https://w.test/2", title="नेपाल", content="काठमाडौं नेपालको राजधानी हो"),
            WebDoc(url="https://w.test/3", title="Dogs", content="dogs bark and sleep"),
        ],
    )


@pytest.fixture
def sandbox(state: SandboxState) -> Sandbox:
    return Sandbox(state)
