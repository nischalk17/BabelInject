from pathlib import Path

import pytest

from aie.secrets import get_secret


def test_environment_wins_over_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = tmp_path / ".env"
    env.write_text("MY_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("MY_KEY", "from-env")
    assert get_secret("MY_KEY", env) == "from-env"


def test_reads_file_tolerating_bom_quotes_comments_and_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("MY_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_bytes(b'\xef\xbb\xbf# comment\nOTHER=1\nexport MY_KEY = "abc123" \n')
    assert get_secret("MY_KEY", env) == "abc123"
    assert get_secret("OTHER", env) == "1"


@pytest.mark.parametrize("content", ["", "MY_KEY=\n", "MY_KEY_2=x\n", "# MY_KEY=x\n"])
def test_missing_or_empty_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: str
) -> None:
    monkeypatch.delenv("MY_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text(content, encoding="utf-8")
    assert get_secret("MY_KEY", env) is None
    assert get_secret("MY_KEY", tmp_path / "nope.env") is None
