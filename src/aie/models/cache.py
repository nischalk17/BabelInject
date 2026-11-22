"""SQLite response cache and the caching model wrapper. All model calls go through here."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path

from aie.models.base import (
    GenConfig,
    Message,
    ModelAdapter,
    ModelConfig,
    ModelResponse,
    ToolSpec,
)


def cache_key(
    model_tag: str,
    messages: Sequence[Message],
    tools: Sequence[ToolSpec],
    cfg: GenConfig,
) -> str:
    """SHA-256 of the canonical JSON of everything that determines a response."""
    payload = {
        "model_tag": model_tag,
        "messages": [m.model_dump() for m in messages],
        "tools": [t.model_dump() for t in tools],
        "cfg": cfg.model_dump(),
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class ResponseCache:
    """Key-value store of model responses in a single SQLite file."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.execute("CREATE TABLE IF NOT EXISTS responses (key TEXT PRIMARY KEY, value TEXT)")
        self._db.commit()

    def get(self, key: str) -> ModelResponse | None:
        """Return the stored response (marked ``cached=True``), or ``None``."""
        row = self._db.execute("SELECT value FROM responses WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        return ModelResponse.model_validate_json(row[0]).model_copy(update={"cached": True})

    def put(self, key: str, resp: ModelResponse) -> None:
        """Store a response under ``key`` (overwrites)."""
        self._db.execute(
            "INSERT OR REPLACE INTO responses (key, value) VALUES (?, ?)",
            (key, resp.model_dump_json()),
        )
        self._db.commit()

    def close(self) -> None:
        """Close the underlying database."""
        self._db.close()


class CachedModel(ModelAdapter):
    """Wraps an adapter; identical requests are served from the cache."""

    def __init__(self, inner: ModelAdapter, cache: ResponseCache) -> None:
        self._inner = inner
        self._cache = cache

    @property
    def model_tag(self) -> str:
        """The wrapped adapter's tag."""
        return self._inner.model_tag

    def chat(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        cfg: GenConfig,
    ) -> ModelResponse:
        """Return a cached response if present, otherwise call the model and store it."""
        key = cache_key(self.model_tag, messages, tools, cfg)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        resp = self._inner.chat(messages, tools, cfg)
        self._cache.put(key, resp)
        return resp


def build_model(cfg: ModelConfig, cache_path: Path) -> ModelAdapter:
    """Build the configured model, always wrapped in the cache."""
    from aie.models.ollama import OllamaAdapter

    if cfg.provider == "ollama":
        inner: ModelAdapter = OllamaAdapter(cfg.model, base_url=cfg.base_url)
    else:  # pragma: no cover - Literal currently allows only ollama
        raise ValueError(f"unknown provider {cfg.provider!r}")
    return CachedModel(inner, ResponseCache(cache_path))
