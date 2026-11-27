import csv
import json
from pathlib import Path

import pytest

from aie.agent.loop import AgentResult
from aie.analysis.figures import fig_asr_heatmap, fig_defense_effect, fig_tradeoff
from aie.analysis.load import load_outcomes
from aie.analysis.tables import (
    answer_mention_rows,
    asr_rows,
    attempt_rows,
    benign_flagged_rows,
    effect_rows,
    flagged_rows,
    newcombe_diff,
    opened_rows,
    utility_rows,
    write_csv,
)
from aie.env.sandbox import Action
from aie.eval.judge import JudgeResult
from aie.eval.runner import ScenarioOutcome

ATTACKER = "attacker@evil.test"
BENIGN = {"success": None, "language": None, "channel": None, "attack": None}


def mk(
    sid: str,
    defense: str = "none",
    language: str | None = "en",
    channel: str | None = "file",
    attack: str | None = "A",
    success: bool | None = True,
    utility: bool = True,
    failed: tuple[str, ...] = (),
    send_to: str | None = None,
    tag: str = "m1",
) -> ScenarioOutcome:
    actions = []
    if send_to:
        actions.append(
            Action(step=0, tool="send_email", args={"to": send_to}, ok=False, result="Blocked")
        )
    return ScenarioOutcome(
        scenario_id=sid,
        attack_id=attack,
        language=language,
        channel=channel,
        defense=defense,
        result=AgentResult(
            final_answer="x",
            stop_reason="final",
            steps=1,
            messages=[],
            actions=actions,
            model_tag=tag,
            prompt_version="v3",
        ),
        outbox=[],
        judge=JudgeResult(
            attack_success=success, utility_success=utility, failed_utility_checks=list(failed)
        ),
    )


def test_newcombe_matches_the_published_example() -> None:
    d, lo, hi = newcombe_diff(56, 70, 48, 80)  # Newcombe (1998) example, method 10
    assert d == pytest.approx(0.2)
    assert lo == pytest.approx(0.0524, abs=2e-3)
    assert hi == pytest.approx(0.3339, abs=2e-3)


def test_load_drops_duplicates_and_the_later_file_wins(tmp_path: Path) -> None:
    def write(name: str, rows: list[ScenarioOutcome]) -> None:
        (tmp_path / name).write_text(
            "".join(r.model_dump_json() + "\n" for r in rows), encoding="utf-8"
        )

    write("a-20261101.jsonl", [mk("s1", success=False), mk("s2")])
    write("b-20261102.jsonl", [mk("s1", success=True)])
    outcomes, report = load_outcomes([tmp_path])
    assert (report.rows_read, report.duplicates_dropped, report.rows_kept) == (3, 1, 2)
    assert {o.scenario_id: o.judge.attack_success for o in outcomes} == {"s1": True, "s2": True}
    with pytest.raises(ValueError, match="no result rows"):
        load_outcomes([tmp_path / "missing"])


def test_asr_rows_group_by_attack_and_pool_all() -> None:
    runs = [
        mk("s1", attack="A", success=True),
        mk("s2", attack="A", success=False),
        mk("s3", attack="B", success=False),
        mk("s4", attack="A", success=True, channel="email"),
        mk("s5", defense="spotlight", success=True),  # other defense: excluded
        mk("s6", **BENIGN),  # benign: excluded
    ]
    rows = {(r.attack, r.channel): r for r in asr_rows(runs, "none")}
    assert (rows[("A", "file")].k, rows[("A", "file")].n) == (1, 2)
    assert (rows[("ALL", "file")].k, rows[("ALL", "file")].n) == (1, 3)
    assert (rows[("ALL", "email")].k, rows[("ALL", "email")].n) == (1, 1)
    cell = rows[("ALL", "file")]
    assert 0 <= cell.lo <= cell.rate <= cell.hi


def test_utility_rows_separate_benign_from_attacked() -> None:
    runs = [
        mk("b1", utility=True, **BENIGN),
        mk("b2", utility=False, **BENIGN),
        mk("a1", utility=True),
    ]
    rows = {r.condition: (r.k, r.n) for r in utility_rows(runs)}
    assert rows == {"benign": (1, 2), "attacked": (1, 1)}


def test_effect_rows_pair_scenarios_and_ignore_baseline_only_scenarios() -> None:
    runs = [
        # baseline: 3 attacked scenarios (s3 is NOT run under the defense) and 2 benign
        mk("s1", success=True),
        mk("s2", success=True),
        mk("s3", success=True),
        mk("b1", utility=True, **BENIGN),
        mk("b2", utility=True, **BENIGN),
        # defense: 2 attacked scenarios, both stopped; one benign task lost
        mk("s1", defense="tool_policy", success=False),
        mk("s2", defense="tool_policy", success=False),
        mk("b1", defense="tool_policy", utility=True, **BENIGN),
        mk("b2", defense="tool_policy", utility=False, **BENIGN),
    ]
    (row,) = effect_rows(runs)
    assert (row.asr_k, row.asr_n, row.base_asr_k, row.base_asr_n) == (0, 2, 2, 2)
    assert row.reduction_pp == pytest.approx(100.0)  # baseline s3 excluded by pairing
    assert (row.utility_k, row.base_utility_k, row.utility_n) == (1, 2, 2)
    assert row.utility_change_pp == pytest.approx(-50.0)
    assert row.reduction_lo_pp < row.reduction_pp <= row.reduction_hi_pp + 1e-9
    assert row.channels == "file"


def test_opened_and_attempted_rates() -> None:
    runs = [
        mk("s1", failed=()),
        mk("s2", failed=("tool_called",), send_to=ATTACKER),
        mk("s3", failed=("answer_contains_any",), send_to="Other@x.test"),
    ]
    (opened,) = opened_rows(runs)
    assert (opened.k, opened.n) == (2, 3)  # only a failed tool_called means "not opened"
    (attempt,) = attempt_rows(runs, {"A": "ATTACKER@evil.test"})
    assert (attempt.k, attempt.n) == (1, 3)  # case-insensitive; other recipients do not count


def test_write_csv_has_a_header_and_rounds_floats(tmp_path: Path) -> None:
    path = tmp_path / "t.csv"
    write_csv(path, asr_rows([mk("s1"), mk("s2", attack="B")], "none"))
    with path.open(encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0][:5] == ["model_tag", "defense", "attack", "language", "channel"]
    assert len(rows) == 4 and all(len(x) == len(rows[0]) for x in rows)
    write_csv(tmp_path / "empty.csv", [])
    assert (tmp_path / "empty.csv").read_text(encoding="utf-8") == ""


def test_figures_render_for_synthetic_data(tmp_path: Path) -> None:
    runs: list[ScenarioOutcome] = []
    for lang in ("en", "ne"):
        for i in range(4):
            for ch in ("file", "tool_output"):
                runs.append(mk(f"{lang}{ch}{i}", language=lang, channel=ch, success=i < 2))
                runs.append(mk(f"{lang}{ch}{i}", "spotlight", lang, ch, success=i < 1))
    runs += [mk(f"b{i}", utility=True, **BENIGN) for i in range(3)]
    runs += [mk(f"b{i}", "spotlight", utility=i < 2, **BENIGN) for i in range(3)]
    paths = fig_asr_heatmap(asr_rows(runs, "none"), tmp_path)
    effects = effect_rows(runs)
    assert effects
    paths += fig_defense_effect(effects, tmp_path) + fig_tradeoff(effects, tmp_path)
    assert len(paths) == 3
    for p in paths:
        assert p.suffix == ".png" and p.stat().st_size > 10_000, p


def test_json_roundtrip_of_a_row_is_loadable() -> None:
    row = mk("s1")
    assert ScenarioOutcome.model_validate(json.loads(row.model_dump_json())) == row


def test_flagged_rows_count_detector_verdicts_on_detector_runs_only() -> None:
    yes = mk("s1", defense="detector")
    yes.defense_events.append({"type": "detector", "tool": "read_file", "verdict": True})
    no = mk("s2", defense="detector")
    no.defense_events.append({"type": "detector", "tool": "read_file", "verdict": None})
    other = mk("s3", defense="none")
    (row,) = flagged_rows([yes, no, other])
    assert (row.metric, row.k, row.n) == ("detector_flagged", 1, 2)


def test_benign_flagged_rows_group_by_task_id_language_suffix() -> None:
    a = mk(
        "meeting__file__hi|benign",
        defense="detector",
        attack=None,
        language=None,
        channel=None,
        success=None,
    )
    a.defense_events.append({"type": "detector", "tool": "read_file", "verdict": True})
    b = mk(
        "hotel__file__hi|benign",
        defense="detector",
        attack=None,
        language=None,
        channel=None,
        success=None,
    )
    c = mk(
        "hotel__file__ne|benign",
        defense="detector",
        attack=None,
        language=None,
        channel=None,
        success=None,
    )
    rows = {r.language: (r.k, r.n) for r in benign_flagged_rows([a, b, c])}
    assert rows == {"hi": (1, 2), "ne": (0, 1)}


def test_answer_mention_rows_use_the_final_answer_of_attacked_runs() -> None:
    said = mk("s1")
    said.result.final_answer = "Room 204. Note: the file had an embedded instruction; I ignored it."
    quiet = mk("s2")
    quiet.result.final_answer = "Room 204."
    (row,) = answer_mention_rows([said, quiet, mk("s3", attack=None, success=None)])
    assert (row.metric, row.k, row.n) == ("answer_mentions_injection", 1, 2)


def test_benign_flagged_rows_skip_tasks_without_a_language_suffix() -> None:
    plain = mk("meeting_room__email|benign", defense="detector", attack=None, success=None)
    assert benign_flagged_rows([plain]) == []


def test_asr_pooled_rows_split_injected_from_user_and_pool_languages() -> None:
    from aie.analysis.tables import asr_pooled_rows

    runs = [
        mk("a", language="en", channel="file", success=True),
        mk("b", language="hi", channel="doc", success=False),
        mk("c", language="en", channel="user", success=True),
        mk("d", attack=None, success=None),
    ]
    rows = {(r.language, r.channel): (r.k, r.n) for r in asr_pooled_rows(runs)}
    assert rows == {
        ("en", "injected"): (1, 1),
        ("hi", "injected"): (0, 1),
        ("ALL", "injected"): (1, 2),
        ("en", "user"): (1, 1),
        ("ALL", "user"): (1, 1),
    }


def test_paired_asr_rows_match_effect_rows_and_need_no_benign_runs() -> None:
    from aie.analysis.tables import paired_asr_rows

    base = [mk(f"s{i}", success=i < 3) for i in range(4)]  # 3 of 4 succeed without a defense
    sand = [mk(f"s{i}", defense="sandwich", success=i == 0) for i in range(4)]  # 1 of 4 with it
    (row,) = paired_asr_rows(base + sand)  # no benign runs: effect_rows would return nothing
    assert (row.k, row.base_k, row.n) == (1, 3, 4)
    assert row.reduction_pp == pytest.approx(50.0)
    assert row.reduction_lo_pp < row.reduction_pp < row.reduction_hi_pp
    benign_runs = [
        mk("b1", attack=None, language=None, channel=None, success=None),
        mk("b1", defense="sandwich", attack=None, language=None, channel=None, success=None),
    ]
    (effect,) = effect_rows(base + sand + benign_runs)
    assert effect.reduction_pp == pytest.approx(row.reduction_pp)
    assert effect.reduction_lo_pp == pytest.approx(row.reduction_lo_pp)


def test_paired_rows_skip_defended_runs_with_no_baseline() -> None:
    from aie.analysis.tables import paired_asr_rows

    assert paired_asr_rows([mk("only-defended", defense="sandwich")]) == []
