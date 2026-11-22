from pathlib import Path

import pytest

from aie.config import ExperimentConfig
from aie.scenarios.grid import build_grid
from aie.scenarios.schema import load_attacks, load_tasks

REPO = Path(__file__).resolve().parent.parent
MODELS = [{"provider": "ollama", "model": "m"}]


@pytest.fixture(autouse=True)
def _repo_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(REPO)


def grid(**overrides: object) -> tuple[list[str], list[str]]:
    cfg = ExperimentConfig.model_validate({"models": MODELS, **overrides})
    tasks = load_tasks(cfg.tasks_file)
    attacks = load_attacks(cfg.attacks_file)
    scenarios, skipped = build_grid(cfg, tasks, attacks)
    return [s.id for s in scenarios], [f"{k.channel}" for k in skipped]


def test_default_grid_is_benign_plus_attack_cells() -> None:
    ids, skipped = grid(channels=["email", "tool_output"])
    assert ids == [
        "latest_email_meeting_room|benign",
        "latest_email_meeting_room|send_email_basic|en|email",
        "latest_email_meeting_room|send_email_basic|en|tool_output",
    ]
    assert skipped == []


def test_benign_can_be_excluded_and_attacks_can_be_emptied() -> None:
    ids, _ = grid(include_benign=False)
    assert ids == ["latest_email_meeting_room|send_email_basic|en|email"]
    ids, _ = grid(attack_ids=[])
    assert ids == ["latest_email_meeting_room|benign"]


def test_channel_without_injection_point_is_skipped_and_reported() -> None:
    ids, skipped = grid(channels=["email", "file"])
    assert "latest_email_meeting_room|send_email_basic|en|file" not in ids
    assert skipped == ["file"]


def test_missing_translation_is_an_error_not_a_skip() -> None:
    with pytest.raises(ValueError, match="no 'ne' payload"):
        grid(languages=["en", "ne"])


def test_unknown_ids_are_errors() -> None:
    with pytest.raises(ValueError, match="unknown task"):
        grid(task_ids=["nope"])
    with pytest.raises(ValueError, match="unknown attack"):
        grid(attack_ids=["nope"])


def test_shipped_configs_expand_to_scenarios() -> None:
    from aie.config import load_config

    for name, expected in [("smoke.yaml", 1), ("mvp.yaml", 3)]:
        cfg = load_config(REPO / "configs" / name)
        scenarios, skipped = build_grid(
            cfg, load_tasks(cfg.tasks_file), load_attacks(cfg.attacks_file)
        )
        assert len(scenarios) == expected, name
        assert skipped == []
        assert cfg.gen.temperature == 0.0
