"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

DATA = Path(__file__).parent / "data"
FIXTURE = DATA / "tiny_source_catalog.parquet"


@pytest.fixture(scope="session")
def tiny_catalog() -> Path:
    """Path to the tiny Roman-like source catalog (generated if missing)."""
    if not FIXTURE.is_file():
        import make_fixture  # noqa: local generator

        make_fixture.main()
    return FIXTURE
