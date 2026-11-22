"""Run one scenario end to end: sandbox + agent loop + deterministic judge."""

from __future__ import annotations

from pydantic import BaseModel

from aie.agent.loop import AgentResult, run_agent
from aie.env.sandbox import Email, Sandbox
from aie.eval.judge import JudgeResult, judge_run
from aie.models.base import GenConfig, ModelAdapter
from aie.scenarios.schema import Scenario


class ScenarioOutcome(BaseModel):
    """Everything about one scenario run; one JSONL row."""

    scenario_id: str
    attack_id: str | None
    language: str | None
    channel: str | None
    result: AgentResult
    outbox: list[Email]
    judge: JudgeResult


def run_scenario(
    model: ModelAdapter,
    scenario: Scenario,
    *,
    cfg: GenConfig | None = None,
    max_steps: int = 8,
) -> ScenarioOutcome:
    """Run the scenario's task in a fresh sandbox and judge the outcome."""
    sandbox = Sandbox(scenario.state)
    result = run_agent(
        model,
        sandbox,
        scenario.task.prompt,
        tools=scenario.task.tools,
        cfg=cfg,
        max_steps=max_steps,
        wrap_tool_output=scenario.wrap_tool_output,
    )
    verdict = judge_run(
        scenario.attack.goal if scenario.attack else None,
        scenario.task.utility,
        result.actions,
        sandbox.outbox,
        result.final_answer,
    )
    return ScenarioOutcome(
        scenario_id=scenario.id,
        attack_id=scenario.attack.id if scenario.attack else None,
        language=scenario.language,
        channel=scenario.channel,
        result=result,
        outbox=list(sandbox.outbox),
        judge=verdict,
    )
