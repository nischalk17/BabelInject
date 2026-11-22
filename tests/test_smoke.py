"""Smoke test: the package imports."""

import aie


def test_package_imports() -> None:
    assert aie.__name__ == "aie"
