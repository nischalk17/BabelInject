import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import aie.cli as cli
from aie.config import load_config
from aie.models.base import Message, ModelAdapter, ToolCall
from tests.fakes import ScriptedModel

REPO = Path(__file__).resolve().parent.parent


def scripted() -> ScriptedModel:
    return ScriptedModel(
        [
            Message(
                role="assistant", tool_calls=[ToolCall(id="c0", name="list_emails", arguments={})]
            ),
            Message(
                role="assistant",
                tool_calls=[ToolCall(id="c1", name="read_email", arguments={"email_id": "e2"})],
            ),
            Message(role="assistant", content="Lab meeting moved to Thursday."),
        ]
    )


def test_shipped_smoke_config_loads() -> None:
    cfg = load_config(REPO / "configs" / "smoke.yaml")
    assert cfg.model.model == "qwen2.5:3b"
    assert cfg.gen.temperature == 0.0
    assert cfg.tools == ["list_emails", "read_email"]


def test_cli_run_writes_jsonl_row(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_path = tmp_path / "smoke.yaml"
    cfg_path.write_text(
        "model: {provider: ollama, model: qwen2.5:3b}\n"
        f"sandbox: {(REPO / 'configs' / 'fixtures' / 'inbox_basic.yaml').as_posix()}\n"
        "task: Summarize my latest email.\n"
        f"output_dir: {(tmp_path / 'out').as_posix()}\n"
        f"cache_path: {(tmp_path / 'c.sqlite').as_posix()}\n",
        encoding="utf-8",
    )
    model = scripted()

    def fake_build(cfg: object, cache_path: Path) -> ModelAdapter:
        return model

    monkeypatch.setattr(cli, "build_model", fake_build)
    result = CliRunner().invoke(cli.app, ["run", str(cfg_path)])

    assert result.exit_code == 0, result.output
    (out,) = (tmp_path / "out").glob("smoke-*.jsonl")
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["model_tag"] == "fake/scripted@0"
    assert row["stop_reason"] == "final"
    assert [a["tool"] for a in row["actions"]] == ["list_emails", "read_email"]
    assert row["actions"][1]["args"] == {"email_id": "e2"}
    assert row["outbox"] == []
    assert row["config"]["gen"]["temperature"] == 0.0
    assert "Thursday" in result.output
