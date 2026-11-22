"""Read secrets (API keys) from the environment or a local ``.env`` file. Never log the values."""

from __future__ import annotations

import os
from pathlib import Path


def get_secret(name: str, env_file: Path = Path(".env")) -> str | None:
    """Return ``name`` from the environment, else from ``env_file`` (``NAME=value`` lines).

    The file is read as UTF-8 and a leading byte-order mark is tolerated, because Windows editors
    sometimes add one. Returns None if the secret is missing or empty.
    """
    value = os.environ.get(name)
    if value:
        return value.strip()
    if not env_file.is_file():
        return None
    for raw in env_file.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.removeprefix("export ").strip()
        key, sep, val = line.partition("=")
        if sep and key.strip() == name:
            val = val.strip().strip("'\"").strip()
            return val or None
    return None
