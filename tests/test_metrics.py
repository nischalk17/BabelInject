import pytest

from aie.agent.loop import AgentResult
from aie.eval.judge import JudgeResult
from aie.eval.metrics import format_cell, rate, summarize, wilson
from aie.eval.runner import ScenarioOutcome


def test_wilson_matches_known_values() -> None:
    lo, hi = wilson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(0.2775, abs=1e-3)
    lo, hi = wilson(5, 10)
    assert (lo, hi) == (pytest.approx(0.2366, abs=1e-3), pytest.approx(0.7634, abs=1e-3))
    lo, hi = wilson(10, 10)
    assert lo == pytest.approx(0.7225, abs=1e-3) and hi == pytest.approx(1.0)


def test_wilson_always_contains_the_point_estimate() -> None:
    for n in range(1, 60):
        for k in range(n + 1):
            lo, hi = wilson(k, n)
            assert 0.0 <= lo <= k / n <= hi <= 1.0, (k, n, lo, hi)


def test_wilson_rejects_bad_counts() -> None:
    for k, n in [(1, 0), (-1, 5), (6, 5)]:
        with pytest.raises(ValueError, match="need n"):
            wilson(k, n)


def outcome(
    tag: str, language: str | None, channel: str | None, attack: bool | None, utility: bool
) -> ScenarioOutcome:
    result = AgentResult(
        final_answer="x",
        stop_reason="final",
        steps=1,
        messages=[],
        actions=[],
        model_tag=tag,
        prompt_version="v3",
    )
    return ScenarioOutcome(
        scenario_id="s",
        attack_id=None if attack is None else "a",
        language=language,
        channel=channel,
        result=result,
        outbox=[],
        judge=JudgeResult(attack_success=attack, utility_success=utility, failed_utility_checks=[]),
    )


def test_summarize_groups_by_model_language_channel() -> None:
    rows = [
        outcome("m1", None, None, None, True),
        outcome("m1", None, None, None, False),
        outcome("m1", "en", "email", True, True),
        outcome("m1", "en", "email", False, True),
        outcome("m1", "en", "email", False, False),
        outcome("m1", "en", "tool_output", False, True),
        outcome("m2", "en", "email", True, True),
    ]
    cells = {(c.model_tag, c.language, c.channel): c for c in summarize(rows)}
    assert len(cells) == 4
    benign = cells[("m1", None, None)]
    assert benign.asr is None and (benign.utility.k, benign.utility.n) == (1, 2)
    email = cells[("m1", "en", "email")]
    assert email.asr is not None and (email.asr.k, email.asr.n) == (1, 3)
    assert (email.utility.k, email.utility.n) == (2, 3)
    assert cells[("m2", "en", "email")].asr == rate(1, 1)


def test_format_cell_shows_counts_and_interval() -> None:
    cells = summarize([outcome("m1", "en", "email", True, True)])
    line = format_cell(cells[0])
    assert "ASR 1/1" in line and "95% CI" in line and "m1 | none | en/email" in line
    assert format_cell(summarize([outcome("m1", None, None, None, True)])[0]).endswith(
        "benign: utility 1/1"
    )
