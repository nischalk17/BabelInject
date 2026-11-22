from pathlib import Path

from aie.models.base import GenConfig, Message, ToolSpec
from aie.models.cache import CachedModel, ResponseCache, cache_key
from tests.fakes import ScriptedModel

MSGS = [Message(role="user", content="hello नेपाली")]
TOOLS = [ToolSpec(name="t", description="d", parameters={"type": "object"})]
CFG = GenConfig()


def test_key_is_stable_and_sensitive_to_every_input() -> None:
    base = cache_key("m", MSGS, TOOLS, CFG)
    assert base == cache_key("m", list(MSGS), list(TOOLS), GenConfig())
    assert base != cache_key("m2", MSGS, TOOLS, CFG)
    assert base != cache_key("m", [Message(role="user", content="other")], TOOLS, CFG)
    assert base != cache_key("m", MSGS, [], CFG)
    assert base != cache_key("m", MSGS, TOOLS, GenConfig(temperature=0.7))
    assert base != cache_key("m", MSGS, TOOLS, GenConfig(seed=1))


def test_cache_hit_skips_inner_model(tmp_path: Path) -> None:
    inner = ScriptedModel([Message(role="assistant", content="answer")])
    model = CachedModel(inner, ResponseCache(tmp_path / "c.sqlite"))
    first = model.chat(MSGS, TOOLS, CFG)
    second = model.chat(MSGS, TOOLS, CFG)
    assert inner.calls == 1
    assert not first.cached
    assert second.cached
    assert second.message == first.message
    assert second.model_tag == "fake/scripted@0"


def test_cache_persists_across_reopen(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "c.sqlite"
    CachedModel(ScriptedModel([Message(role="assistant", content="x")]), ResponseCache(path)).chat(
        MSGS, TOOLS, CFG
    )
    inner = ScriptedModel([])
    resp = CachedModel(inner, ResponseCache(path)).chat(MSGS, TOOLS, CFG)
    assert inner.calls == 0
    assert resp.message.content == "x"
