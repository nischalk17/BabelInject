import json
from pathlib import Path

from aie.analysis.completeness import check_completeness, format_completeness


def write(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def row(
    sid: str, defense: str = "none", tag: str = "m1", config: str = "c.yaml"
) -> dict[str, object]:
    return {
        "config_name": config,
        "scenario_id": sid,
        "defense": defense,
        "result": {"model_tag": tag},
    }


def test_complete_grid_passes(tmp_path: Path) -> None:
    write(tmp_path / "a-1.jsonl", [row("s1"), row("s2")])
    c = check_completeness("c.yaml", ["s1", "s2"], ["none"], 1, [tmp_path])
    assert c.complete and c.cells[0].found == 2
    assert "complete" in format_completeness(c)


def test_missing_scenarios_are_named_and_other_configs_are_ignored(tmp_path: Path) -> None:
    write(tmp_path / "a-1.jsonl", [row("s1"), row("s9", config="other.yaml")])
    c = check_completeness("c.yaml", ["s1", "s2", "s3"], ["none"], 1, [tmp_path])
    assert not c.complete
    assert c.cells[0].missing == ["s2", "s3"] and c.cells[0].found == 1
    text = format_completeness(c)
    assert "INCOMPLETE" in text and "s2" in text


def test_a_rerun_counts_once_and_extra_rows_are_reported(tmp_path: Path) -> None:
    write(tmp_path / "a-1.jsonl", [row("s1"), row("zz")])
    write(tmp_path / "b-2.jsonl", [row("s1"), row("s2")])
    c = check_completeness("c.yaml", ["s1", "s2"], ["none"], 1, [tmp_path])
    assert c.complete and c.cells[0].found == 2 and c.cells[0].unexpected == 1


def test_a_missing_defense_or_model_makes_the_grid_incomplete(tmp_path: Path) -> None:
    write(tmp_path / "a-1.jsonl", [row("s1")])
    no_defense = check_completeness("c.yaml", ["s1"], ["none", "sandwich"], 1, [tmp_path])
    assert not no_defense.complete
    no_model = check_completeness("c.yaml", ["s1"], ["none"], 2, [tmp_path])
    assert no_model.models_missing == 1 and not no_model.complete
    assert not check_completeness("c.yaml", ["s1"], ["none"], 1, [tmp_path / "nowhere"]).cells
