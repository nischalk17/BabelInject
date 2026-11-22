"""Tool implementations and registry. Pure functions over a ``Sandbox``."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict

from aie.env.sandbox import Email, Sandbox
from aie.models.base import ToolSpec


class ToolError(Exception):
    """A tool failed in a way the agent should see as text (e.g. missing email)."""


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ListEmailsArgs(_Args):
    limit: int = 10


class ReadEmailArgs(_Args):
    email_id: str


class ReadFileArgs(_Args):
    path: str


class SearchWebArgs(_Args):
    query: str
    k: int = 3


class FetchUrlArgs(_Args):
    url: str


class SendEmailArgs(_Args):
    to: str
    subject: str
    body: str


class NoArgs(_Args):
    pass


def list_emails(sb: Sandbox, limit: int = 10) -> str:
    """List inbox emails, newest first."""
    emails = sorted(sb.state.inbox, key=lambda e: e.date, reverse=True)[: max(limit, 0)]
    if not emails:
        return "Inbox is empty."
    return "\n".join(f"{e.id} | {e.date} | {e.sender} | {e.subject}" for e in emails)


def read_email(sb: Sandbox, email_id: str) -> str:
    """Return the full text of one email."""
    for e in sb.state.inbox:
        if e.id == email_id:
            return (
                f"From: {e.sender}\nTo: {', '.join(e.to)}\nDate: {e.date}\n"
                f"Subject: {e.subject}\n\n{e.body}"
            )
    raise ToolError(f"no email with id {email_id!r}")


def list_files(sb: Sandbox) -> str:
    """List file paths in the fake file store."""
    return "\n".join(sorted(sb.state.files)) or "No files."


def read_file(sb: Sandbox, path: str) -> str:
    """Return the contents of a file."""
    if path not in sb.state.files:
        raise ToolError(f"no such file {path!r}")
    return sb.state.files[path]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def search_web(sb: Sandbox, query: str, k: int = 3) -> str:
    """Rank web/RAG docs by token overlap with the query (deterministic, Unicode-aware)."""
    q = _tokens(query)
    scored = [
        (len(q & _tokens(f"{d.title} {d.content}")), i, d) for i, d in enumerate(sb.state.web)
    ]
    hits = sorted((s for s in scored if s[0] > 0), key=lambda s: (-s[0], s[1]))[: max(k, 0)]
    if not hits:
        return "No results."
    return "\n\n".join(f"{d.url}\n{d.title}\n{d.content}" for _, _, d in hits)


def fetch_url(sb: Sandbox, url: str) -> str:
    """Return a page from the fake web store."""
    for d in sb.state.web:
        if d.url == url:
            return f"{d.title}\n\n{d.content}"
    raise ToolError(f"could not fetch {url!r}")


def send_email(sb: Sandbox, to: str, subject: str, body: str) -> str:
    """Queue an email in the sandbox outbox. Nothing is ever sent."""
    sb.outbox.append(
        Email(
            id=f"out{len(sb.outbox) + 1}",
            sender=sb.state.user_email,
            to=[to],
            subject=subject,
            body=body,
            date="sandbox",
        )
    )
    return f"Email sent to {to}."


@dataclass(frozen=True)
class Tool:
    """A registered tool: its schema, argument model and implementation."""

    name: str
    description: str
    args_model: type[BaseModel]
    fn: Callable[..., str]


TOOLS: dict[str, Tool] = {
    t.name: t
    for t in [
        Tool("list_emails", "List emails in the inbox, newest first.", ListEmailsArgs, list_emails),
        Tool("read_email", "Read the full text of an email by id.", ReadEmailArgs, read_email),
        Tool("list_files", "List files in the user's file store.", NoArgs, list_files),
        Tool("read_file", "Read a file by path.", ReadFileArgs, read_file),
        Tool("search_web", "Search the web knowledge base.", SearchWebArgs, search_web),
        Tool("fetch_url", "Fetch a web page by URL.", FetchUrlArgs, fetch_url),
        Tool("send_email", "Send an email to a recipient.", SendEmailArgs, send_email),
    ]
}


def _strip_titles(schema: dict[str, Any]) -> dict[str, Any]:
    schema.pop("title", None)
    for prop in schema.get("properties", {}).values():
        prop.pop("title", None)
    return schema


def tool_specs(names: Sequence[str] | None = None) -> list[ToolSpec]:
    """Model-facing specs for the named tools (all tools if ``names`` is None)."""
    chosen = list(TOOLS) if names is None else list(names)
    return [
        ToolSpec(
            name=n,
            description=TOOLS[n].description,
            parameters=_strip_titles(TOOLS[n].args_model.model_json_schema()),
        )
        for n in chosen
    ]
