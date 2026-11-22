"""Run one scenario end to end: sandbox + defense + agent loop + deterministic judge."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from aie.agent.loop import AgentResult, run_agent
from aie.agent.prompts import SYSTEM_PROMPT
from aie.defenses import DefenseConfig, DefenseContext, build_defense
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
    defense: str = "none"
    defense_version: str = "none-v1"
    defense_events: list[dict[str, Any]] = Field(default_factory=list)
    result: AgentResult
    outbox: list[Email]
    judge: JudgeResult


def run_scenario(
    model: ModelAdapter,
    scenario: Scenario,
    *,
    cfg: GenConfig | None = None,
    max_steps: int = 8,
    defense_cfg: DefenseConfig | None = None,
    detector_model: ModelAdapter | None = None,
) -> ScenarioOutcome:
    """Run the scenario's task in a fresh sandbox, under the chosen defense, and judge it.

    Order of text transformations on a tool result: first the attack payload is injected (for the
    ``tool_output`` channel), then the defense wraps the result, so the defense sees what the model
    would have seen undefended.
    """
    gen = cfg or GenConfig()
    sandbox = Sandbox(scenario.state)
    defense = build_defense(
        defense_cfg or DefenseConfig(),
        DefenseContext(
            task=scenario.task.prompt,
            state=scenario.state,
            detector_model=detector_model or model,
            gen=gen,
        ),
    )

    def view(tool_name: str, output: str) -> str:
        return defense.wrap_tool_output(tool_name, scenario.wrap_tool_output(tool_name, output))

    result = run_agent(
        model,
        sandbox,
        scenario.task.prompt,
        tools=scenario.task.tools,
        cfg=gen,
        max_steps=max_steps,
        wrap_tool_output=view,
        system_prompt=defense.system_prompt(SYSTEM_PROMPT),
        authorize=defense.authorize,
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
        defense=defense.name,
        defense_version=defense.version,
        defense_events=list(defense.events),
        result=result,
        outbox=list(sandbox.outbox),
        judge=verdict,
    )
