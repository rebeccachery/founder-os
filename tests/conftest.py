"""Shared fixtures: every test gets an isolated database and the example profiles.

Tests never touch ``storage/founder_os.db`` or ``private/`` and never hit the network.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

# Set before any app module is imported (api.deps reads API_KEY at import time).
os.environ.setdefault("API_KEY", "test-key")
os.environ["SEED_DEMO_DATA"] = "false"
# Empty (not unset) so api.main's load_dotenv() can't pull real keys from a
# developer's .env — python-dotenv never overrides variables that already exist.
for _key in ("TAVILY_API_KEY", "SERPAPI_KEY", "GOOGLE_CSE_KEY", "GOOGLE_CSE_CX", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
    os.environ[_key] = ""
os.environ["LLM_PROVIDER"] = "none"

TODAY = date(2026, 6, 1)  # fixed clock for date-dependent assertions


@pytest.fixture(autouse=True)
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    # Empty private dir → config resolution falls back to config/*.example.yaml.
    monkeypatch.setenv("FOUNDER_OS_PRIVATE_DIR", str(tmp_path / "private"))
    yield tmp_path


@pytest.fixture
def conn(isolated_env: Path):
    from lib.db import get_connection, init_db

    init_db()
    with get_connection() as connection:
        yield connection


@pytest.fixture
def founder_profile():
    from lib.scout.profile import load_founder_profile

    return load_founder_profile()
