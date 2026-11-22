"""No defense: the baseline."""

from __future__ import annotations

from aie.defenses.base import Defense


class NoDefense(Defense):
    """Leaves the prompt, the tool output and the tool calls untouched."""

    name = "none"
    version = "none-v1"
