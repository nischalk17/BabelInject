import csv
import json
from pathlib import Path
from typing import Any

import pytest

from aie.analysis.demo_export import (
    DemoConfig,
    StudyConfig,
    build_summary_and_meta,
    dumps,
    export,
    load_demo_config,
)
from aie.analysis.report import build_tables
from aie.analysis.tables import attacked_utility_rows
from tests.test_analysis import mk

REPO = Path(__file__).resolve().parent.parent
ATTACKS = "src/aie/scenarios/attacks.yaml"
NO_ATTACK: dict[str, Any] = {"attack": None, "language": None, "channel": None, "success": None}


def _write(root: Path, folder: str, rows: list[Any]) -> None:
    d = root / folder
    d.mkdir(parents=True, exist_ok=True)
    lines = []
    for r in rows:
        row = json.loads(r.model_dump_json())
        row["started_at"] = "2026-11-23T10:00:00"
        lines.append(json.dumps(row))
    (d / "run.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def fixture_root(tmp_path: Path) -> Path:
    (tmp_path / "src/aie/scenarios").mkdir(parents=True)
    (tmp_path / ATTACKS).write_text((REPO / ATTACKS).read_text(encoding="utf-8"), encoding="utf-8")
    ov, note = "inject_override", "inject_owner_note"
    runs = [
        mk("t1|a|en|file", attack=ov, success=True),
        mk("t2|a|en|file", attack=ov, success=False, utility=False),
        mk("t3|b|en|file", attack=note, success=False),
        mk("t1|a|hi|file", language="hi", attack=ov, success=False),
        mk("t1|benign", **NO_ATTACK),
        mk("t1|a|en|file", defense="detector", attack=ov, success=False),
        mk("t1|benign", defense="detector", **NO_ATTACK),
    ]
    _write(tmp_path, "results/a", runs)
    return tmp_path


def _cfg() -> DemoConfig:
    study = StudyConfig(
        id="main",
        title="t",
        attacks_file=Path(ATTACKS),
        inputs=[Path("results/a"), Path("results/none")],
    )
    return DemoConfig(
        repo_url="https://example.test/r",
        report_url="https://example.test/r/report",
        studies=[study],
    )


def test_summary_cells_equal_the_summary_csv_tables(fixture_root: Path) -> None:
    summary, _ = build_summary_and_meta(_cfg(), fixture_root, commit="abc")
    out = fixture_root / "csv"
    build_tables([fixture_root / "results/a"], out, fixture_root / ATTACKS)
    cells = {
        (c["model_tag"], c["defense"], c["attack"], c["language"], c["channel"]): c["asr"]
        for c in summary["studies"][0]["cells"]
    }
    checked = 0
    for name in ("table1_asr_language_channel.csv", "table2b_asr_by_defense.csv"):
        for row in csv.DictReader((out / name).open(encoding="utf-8")):
            key = (row["model_tag"], row["defense"], row["attack"], row["language"], row["channel"])
            got = cells[key]
            assert (got["k"], got["n"]) == (int(row["k"]), int(row["n"]))
            for field in ("rate", "lo", "hi"):
                assert got[field] == pytest.approx(float(row[field]), abs=5e-5)
            checked += 1
    assert checked > 0


def test_wilson_interval_values_are_the_published_ones(fixture_root: Path) -> None:
    summary, _ = build_summary_and_meta(_cfg(), fixture_root, commit="abc")
    en_file = next(
        c
        for c in summary["studies"][0]["cells"]
        if (c["defense"], c["attack"], c["language"], c["channel"])
        == ("none", "inject_override", "en", "file")
    )
    assert (en_file["asr"]["k"], en_file["asr"]["n"]) == (1, 2)
    assert en_file["asr"]["lo"] == pytest.approx(0.0945, abs=1e-3)  # Wilson 95% for 1 of 2
    assert en_file["asr"]["hi"] == pytest.approx(0.9055, abs=1e-3)


def test_all_cells_carry_extras_and_per_attack_cells_do_not(fixture_root: Path) -> None:
    summary, _ = build_summary_and_meta(_cfg(), fixture_root, commit="abc")
    cells = summary["studies"][0]["cells"]
    all_cell = next(
        c for c in cells if (c["attack"], c["defense"], c["language"]) == ("ALL", "none", "en")
    )
    assert all_cell["attacked_utility"]["n"] == 3 and all_cell["attacked_utility"]["k"] == 2
    one = next(c for c in cells if c["attack"] == "inject_override" and c["language"] == "en")
    assert "attacked_utility" not in one
    assert summary["studies"][0]["benign"][0]["utility"]["n"] == 1


def test_missing_inputs_give_a_not_run_study_without_numbers(tmp_path: Path) -> None:
    (tmp_path / "src/aie/scenarios").mkdir(parents=True)
    summary, meta = build_summary_and_meta(_cfg(), tmp_path, commit="abc")
    study = summary["studies"][0]
    assert study["status"] == "not_run" and study["cells"] == []
    assert meta["scenarios_by_study"] == {"main": 0} and meta["models"] == []


def test_meta_has_provenance_and_no_wall_clock(fixture_root: Path) -> None:
    _, meta = build_summary_and_meta(_cfg(), fixture_root, commit="abc")
    assert meta["git_commit"] == "abc" and meta["repo_url"].startswith("https://")
    (model,) = meta["models"]
    assert (model["tag"], model["first_run"], model["last_run"]) == (
        "m1",
        "2026-11-23",
        "2026-11-23",
    )
    assert "generated_at" not in meta and meta["scenarios_by_study"] == {"main": 7}


def test_export_is_byte_identical_on_a_second_run(fixture_root: Path) -> None:
    first = [p.read_bytes() for p in export(_cfg(), fixture_root, fixture_root / "o1", "abc")]
    second = [p.read_bytes() for p in export(_cfg(), fixture_root, fixture_root / "o2", "abc")]
    assert first == second and b"\r\n" not in first[0]
    assert dumps({"b": 1.23456789, "a": 1}).startswith('{\n "a": 1')


def test_attacked_utility_rows_pool_over_attacks() -> None:
    runs = [mk("a", utility=True), mk("b", utility=False), mk("c", **NO_ATTACK)]
    (row,) = attacked_utility_rows(runs)
    assert (row.metric, row.k, row.n) == ("attacked_utility", 1, 2)


def test_studies_config_loads_and_names_real_attack_files() -> None:
    cfg = load_demo_config(REPO / "configs" / "demo_studies.yaml")
    assert [s.id for s in cfg.studies] == ["main", "quiet", "detector_langs"]
    assert all((REPO / s.attacks_file).is_file() for s in cfg.studies)


def _rows(name: str) -> list[dict[str, str]]:
    with (REPO / "results/summary" / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_committed_summary_csvs_are_reproduced_by_the_export() -> None:
    """Real-data check: every committed table1/2b/2/4/5 row appears unchanged in summary.json."""
    if not (REPO / "results/full").is_dir():
        pytest.skip("raw results are not committed; this runs only where results/ exists")
    cfg = load_demo_config(REPO / "configs/demo_studies.yaml")
    summary, _ = build_summary_and_meta(cfg, REPO, "x")
    main = next(s for s in summary["studies"] if s["id"] == "main")
    cells = {
        (c["model_tag"], c["defense"], c["attack"], c["language"], c["channel"]): c
        for c in main["cells"]
    }
    for name in ("table1_asr_language_channel.csv", "table2b_asr_by_defense.csv"):
        for row in _rows(name):
            key = (row["model_tag"], row["defense"], row["attack"], row["language"], row["channel"])
            got = cells[key]["asr"]
            assert (got["k"], got["n"]) == (int(row["k"]), int(row["n"]))
            for field in ("rate", "lo", "hi"):
                assert got[field] == pytest.approx(float(row[field]), abs=5e-5)
    extras = {
        "table4_item_opened.csv": "item_opened",
        "table5_attack_attempted.csv": "attack_attempted",
    }
    for name, field in extras.items():
        for row in _rows(name):
            key = (row["model_tag"], row["defense"], "ALL", row["language"], row["channel"])
            assert (cells[key][field]["k"], cells[key][field]["n"]) == (
                int(row["k"]),
                int(row["n"]),
            )
    effects = {(e["model_tag"], e["defense"], e["language"]): e for e in main["effects"]}
    for row in _rows("table2_defense_effect.csv"):
        e = effects[(row["model_tag"], row["defense"], row["language"])]
        assert (e["asr_k"], e["asr_n"]) == (int(row["asr_k"]), int(row["asr_n"]))
        assert e["reduction_pp"] == pytest.approx(float(row["reduction_pp"]), abs=1e-3)


def test_pooled_rollups_equal_the_pooled_csv_table(fixture_root: Path) -> None:
    summary, _ = build_summary_and_meta(_cfg(), fixture_root, commit="abc")
    out = fixture_root / "csv_pooled"
    build_tables([fixture_root / "results/a"], out, fixture_root / ATTACKS)
    pooled = {
        (p["model_tag"], p["defense"], p["language"], p["channel"]): p
        for p in summary["studies"][0]["pooled"]
    }
    rows = list(csv.DictReader((out / "table10_asr_pooled.csv").open(encoding="utf-8")))
    assert rows and len(rows) == len(pooled)
    for row in rows:
        got = pooled[(row["model_tag"], row["defense"], row["language"], row["channel"])]
        assert (got["k"], got["n"]) == (int(row["k"]), int(row["n"]))
        assert got["lo"] == pytest.approx(float(row["lo"]), abs=5e-5)


def test_paired_rows_in_summary_equal_the_paired_csv(fixture_root: Path) -> None:
    summary, _ = build_summary_and_meta(_cfg(), fixture_root, commit="abc")
    out = fixture_root / "csv_paired"
    build_tables([fixture_root / "results/a"], out, fixture_root / ATTACKS)
    paired = summary["studies"][0]["paired"]
    rows = list(csv.DictReader((out / "table11_defense_paired.csv").open(encoding="utf-8")))
    assert rows and len(rows) == len(paired)
    for row, got in zip(rows, paired, strict=True):
        assert (got["k"], got["base_k"], got["n"]) == (
            int(row["k"]),
            int(row["base_k"]),
            int(row["n"]),
        )
        assert got["reduction_pp"] == pytest.approx(float(row["reduction_pp"]), abs=1e-3)
