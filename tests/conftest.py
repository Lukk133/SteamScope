"""Wspólne fixtury pytestowe dla całego projektu."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def sample_steam_api_payload() -> dict:
    return json.loads((FIXTURES_DIR / "sample_steam_api.json").read_text(encoding="utf-8"))


@pytest.fixture
def sample_steamspy_payload() -> dict:
    return json.loads((FIXTURES_DIR / "sample_steamspy.json").read_text(encoding="utf-8"))


@pytest.fixture
def sample_reviews_html() -> str:
    return (FIXTURES_DIR / "sample_reviews.html").read_text(encoding="utf-8")


@pytest.fixture
def tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Przekierowuje PATHS na katalog tymczasowy dla testów dotykających dysku."""
    from backend import config

    new_paths = config.Paths(project_root=tmp_path)
    monkeypatch.setattr(config, "PATHS", new_paths)
    new_paths.ensure()
    return tmp_path
