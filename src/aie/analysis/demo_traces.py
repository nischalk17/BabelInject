"""Featured traces for the Results Explorer: real runs from ``results/``, rewritten for display.

Nothing is invented. A trace is one stored row; this module only (1) finds it, (2) marks where the
attack text sits in what the model saw, (3) attaches the defense events, and (4) re-runs the
deterministic judge on the stored actions and refuses to export if its verdict differs from the
stored one. The "rule that decided it" comes from the attack goal and the task's utility checks.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import BaseModel, ConfigDict

from aie.analysis.load import expand
from aie.env.sandbox import Email
from aie.eval.judge import judge_run, utility_check_passes
from aie.eval.runner import ScenarioOutcome
from aie.scenarios.schema import (
    AnswerContainsAnyCheck,
    AnyToolCalledCheck,
    Attack,
    EmailSentCheck,
    ExfiltrateFileGoal,
    Language,
    SendEmailGoal,
    Task,
    ToolCalledCheck,
    UtilityCheck,
    load_attacks,
    load_tasks,
    normalize,
)

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
TASK_FILES = [
    "src/aie/scenarios/tasks.yaml",
    "configs/control_tasks.yaml",
    "configs/benign_control_tasks.yaml",
]
ATTACK_FILES = ["src/aie/scenarios/attacks.yaml", "configs/attacks_quiet.yaml"]


class TraceSpec(BaseModel):
    """One featured trace: which stored run, and why it is shown."""

    model_config = ConfigDict(extra="forbid")

    id: str
    model_tag: str
    defense: str
    scenario_id: str
    title: str
    why: str
    pair_with: str | None = None


class TracesConfig(BaseModel):
    """``configs/demo_traces.yaml``."""

    model_config = ConfigDict(extra="forbid")

    traces: list[TraceSpec]


def load_traces_config(path: Path) -> TracesConfig:
    """Load and validate the featured-trace list; ids must be unique slugs."""
    cfg = TracesConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    ids = [t.id for t in cfg.traces]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate trace ids in the featured-trace config")
    for t in cfg.traces:
        if not SLUG.match(t.id):
            raise ValueError(f"trace id {t.id!r} must be a lowercase slug")
        if t.pair_with is not None and t.pair_with not in ids:
            raise ValueError(f"trace {t.id!r}: pair_with {t.pair_with!r} is not a featured trace")
    return cfg


def load_raw_rows(inputs: Sequence[Path]) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Raw JSONL rows keyed like :func:`aie.analysis.load.load_outcomes` (later files win)."""
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for f in expand(inputs):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            key = (row["result"]["model_tag"], row.get("defense", "none"), row["scenario_id"])
            rows[key] = row
    return rows


def describe_check(check: UtilityCheck) -> str:
    """One plain sentence for a utility check."""
    if isinstance(check, ToolCalledCheck):
        args = ", ".join(f"{k}={v}" for k, v in check.args.items())
        return f"The agent called {check.tool}" + (f" with {args}." if args else ".")
    if isinstance(check, AnyToolCalledCheck):
        return f"The agent called one of: {', '.join(check.tools)}."
    if isinstance(check, AnswerContainsAnyCheck):
        return "The final answer contains: " + " or ".join(repr(v) for v in check.values) + "."
    if isinstance(check, EmailSentCheck):
        return f"An email was sent to {check.to}."
    raise TypeError(f"unknown check {check!r}")  # pragma: no cover


def _goal_text(attack: Attack) -> str:
    goal = attack.goal
    if isinstance(goal, SendEmailGoal):
        extra = f" containing {goal.body_contains!r}" if goal.body_contains else ""
        return f"The attack succeeds if the sandbox outbox holds an email to {goal.to}{extra}."
    if isinstance(goal, ExfiltrateFileGoal):
        return (
            f"The attack succeeds if the agent read {goal.path} and emailed its marker to "
            f"{goal.to}."
        )
    raise TypeError(f"unknown goal {goal!r}")  # pragma: no cover


def _matched_email(attack: Attack, outbox: Sequence[Email]) -> dict[str, Any] | None:
    to = getattr(attack.goal, "to", None)
    if to is None:
        return None
    for e in outbox:
        if normalize(to) in {normalize(r) for r in e.to}:
            return {"to": e.to, "subject": e.subject, "body": e.body}
    return None


def _spans(text: str, payload: str) -> list[list[int]]:
    out: list[list[int]] = []
    start = text.find(payload)
    while start != -1:
        out.append([start, start + len(payload)])
        start = text.find(payload, start + len(payload))
    return out


def _events_by_message(
    outcome: ScenarioOutcome, tool_indices: Sequence[int]
) -> dict[int, list[dict[str, Any]]]:
    """Attach defense events to the tool message they belong to.

    Detector events are one per tool result, in order. Tool-policy events name the blocked call, so
    they go to the tool message of the matching failed ``send_email`` action.
    """
    by_msg: dict[int, list[dict[str, Any]]] = {}
    detector = [e for e in outcome.defense_events if e.get("type") == "detector"]
    if detector and len(detector) == len(tool_indices):
        for idx, event in zip(tool_indices, detector, strict=True):
            by_msg.setdefault(idx, []).append(event)
    blocked = [e for e in outcome.defense_events if e.get("type") == "blocked"]
    failed = [
        (idx, a)
        for idx, a in zip(tool_indices, outcome.result.actions, strict=False)
        if a.tool == "send_email" and not a.ok
    ]
    for event, (idx, _) in zip(blocked, failed, strict=False):
        by_msg.setdefault(idx, []).append(event)
    return by_msg


def _steps(
    outcome: ScenarioOutcome, payload: str | None, channel: str | None
) -> tuple[str, list[dict[str, Any]], bool]:
    """Display steps, the system prompt, and whether the payload was located."""
    msgs = outcome.result.messages
    calls: dict[str, tuple[str, dict[str, Any]]] = {}
    tool_indices = [i for i, m in enumerate(msgs) if m.role == "tool"]
    events = _events_by_message(outcome, tool_indices)
    actions = list(outcome.result.actions)
    steps: list[dict[str, Any]] = []
    located = False
    system = ""
    n_tool = 0
    for i, m in enumerate(msgs):
        if m.role == "system":
            system = m.content
            continue
        step: dict[str, Any] = {"i": len(steps), "text": m.content, "injection_spans": []}
        if m.role == "user":
            step["kind"] = "user"
            if payload and channel == "user":
                step["injection_spans"] = _spans(m.content, payload)
                located = located or bool(step["injection_spans"])
        elif m.role == "assistant":
            step["kind"] = "assistant" if m.tool_calls else "final"
            step["tool_calls"] = [{"name": c.name, "args": c.arguments} for c in m.tool_calls]
            for c in m.tool_calls:
                calls[c.id] = (c.name, c.arguments)
        else:
            name, args = calls.get(m.tool_call_id or "", ("?", {}))
            action = actions[n_tool] if n_tool < len(actions) else None
            n_tool += 1
            step["kind"] = "tool"
            step["tool"] = {"name": name, "args": args, "ok": None if action is None else action.ok}
            if payload and channel != "user":
                step["injection_spans"] = _spans(m.content, payload)
                located = located or bool(step["injection_spans"])
        if i in events:
            step["events"] = events[i]
        steps.append(step)
    return system, steps, located


def build_trace(
    spec: TraceSpec,
    raw: dict[str, Any],
    tasks: dict[str, Task],
    attacks: dict[str, Attack],
) -> dict[str, Any]:
    """One trace dict from one stored row.

    Raises if the re-run judge disagrees with the stored verdict.
    """
    outcome = ScenarioOutcome.model_validate(raw)
    task = tasks[outcome.scenario_id.split("|")[0]]
    attack = attacks[outcome.attack_id] if outcome.attack_id else None
    language, channel = outcome.language, outcome.channel
    payload = attack.payloads[cast(Language, language)] if attack and language else None
    verdict = judge_run(
        attack.goal if attack else None,
        task.utility,
        outcome.result.actions,
        outcome.outbox,
        outcome.result.final_answer,
    )
    if verdict != outcome.judge:
        raise ValueError(
            f"{spec.id}: re-run judge {verdict.model_dump()} != stored {outcome.judge.model_dump()}"
        )
    system, steps, located = _steps(outcome, payload, channel)
    detector_removed = any(e.get("verdict") is True for e in outcome.defense_events)
    injection: dict[str, Any] | None = None
    if attack and payload:
        injection = {
            "attack_id": attack.id,
            "language": language,
            "channel": channel,
            "payload": payload,
            "located": located,
            "note": (
                None
                if located
                else "The detector removed the tool result before the model saw it."
                if detector_removed
                else "The payload text was not found verbatim in what the model saw."
            ),
        }
    checks = [
        {
            "type": c.type,
            "text": describe_check(c),
            "passed": utility_check_passes(
                c, outcome.result.actions, outcome.outbox, outcome.result.final_answer
            ),
        }
        for c in task.utility
    ]
    blocked_attempts = [
        {"args": a.args, "result": a.result}
        for a in outcome.result.actions
        if attack is not None
        and a.tool == "send_email"
        and not a.ok
        and normalize(str(a.args.get("to", ""))) == normalize(str(getattr(attack.goal, "to", "")))
    ]
    return {
        "id": spec.id,
        "title": spec.title,
        "why_featured": spec.why,
        "pair_with": spec.pair_with,
        "model_tag": outcome.result.model_tag,
        "run_date": str(raw.get("started_at", ""))[:10] or None,
        "config_name": raw.get("config_name"),
        "gen": raw.get("gen"),
        "prompt_version": outcome.result.prompt_version,
        "defense": {"name": outcome.defense, "version": outcome.defense_version},
        "scenario": {
            "scenario_id": outcome.scenario_id,
            "task_id": task.id,
            "attack_id": outcome.attack_id,
            "language": language,
            "channel": channel,
        },
        "task_prompt": next((m.content for m in outcome.result.messages if m.role == "user"), ""),
        "system_prompt": system,
        "injection": injection,
        "steps": steps,
        "stop_reason": outcome.result.stop_reason,
        "outbox": [e.model_dump() for e in outcome.outbox],
        "verdict": {
            "attack_success": outcome.judge.attack_success,
            "utility_success": outcome.judge.utility_success,
            "failed_utility_checks": outcome.judge.failed_utility_checks,
            "rule": None
            if attack is None
            else {
                "id": attack.goal.type,
                "text": _goal_text(attack),
                "matched_email": _matched_email(attack, outcome.outbox),
                "blocked_attempts": blocked_attempts,
            },
            "utility_checks": checks,
        },
    }


def build_traces(cfg: TracesConfig, inputs: Sequence[Path], root: Path) -> list[dict[str, Any]]:
    """Resolve every featured trace; a missing run is an error, never skipped."""
    raws = load_raw_rows([root / p for p in inputs])
    tasks = {t.id: t for f in TASK_FILES for t in load_tasks(root / f)}
    attacks = {a.id: a for f in ATTACK_FILES for a in load_attacks(root / f)}
    out = []
    for spec in cfg.traces:
        raw = raws.get((spec.model_tag, spec.defense, spec.scenario_id))
        if raw is None:
            raise ValueError(
                f"{spec.id}: no stored run for {spec.model_tag} {spec.defense} {spec.scenario_id}"
            )
        out.append(build_trace(spec, raw, tasks, attacks))
    return out


def trace_index(traces: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """The small list the site loads first (one entry per trace, no steps)."""
    return [
        {
            "id": t["id"],
            "title": t["title"],
            "why_featured": t["why_featured"],
            "pair_with": t["pair_with"],
            "model_tag": t["model_tag"],
            "run_date": t["run_date"],
            "defense": t["defense"]["name"],
            "attack_id": t["scenario"]["attack_id"],
            "language": t["scenario"]["language"],
            "channel": t["scenario"]["channel"],
            "attack_success": t["verdict"]["attack_success"],
            "utility_success": t["verdict"]["utility_success"],
        }
        for t in traces
    ]
