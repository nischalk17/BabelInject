"""Tool-permission policy: only allow email to people the user already knows.

This defense never reads the text of the attack, so it does not depend on the attack's language.
Limitation: it only stops sending to unknown addresses, not abuse of a known contact.
"""

from __future__ import annotations

from aie.defenses.base import Defense
from aie.env.sandbox import SandboxState
from aie.models.base import ToolCall
from aie.scenarios.schema import normalize


def known_contacts(state: SandboxState) -> set[str]:
    """The user's own address plus every sender and recipient in the starting inbox."""
    people = {state.user_email}
    for email in state.inbox:
        people.add(email.sender)
        people.update(email.to)
    return {normalize(p) for p in people}


class ToolPolicy(Defense):
    """Block ``send_email`` unless the recipient is a known contact."""

    name = "tool_policy"
    version = "tool_policy-v1"

    def __init__(self, state: SandboxState) -> None:
        super().__init__()
        self._contacts = known_contacts(state)

    def authorize(self, call: ToolCall) -> str | None:
        """Return a refusal for emails to unknown recipients."""
        if call.name != "send_email":
            return None
        to = call.arguments.get("to")
        if isinstance(to, str) and normalize(to) in self._contacts:
            return None
        self.events.append({"type": "blocked", "tool": call.name, "to": str(to)})
        return f"Blocked by policy: {to!s} is not a known contact, so the email was not sent."
