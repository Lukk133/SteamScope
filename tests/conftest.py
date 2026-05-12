"""Wspólne fixtury pytestowe dla całego projektu."""
# Fixtury sample_steam_api_payload / sample_steamspy_payload / sample_reviews_html
# czytają pliki z tests/fixtures/ tworzone w późniejszych zadaniach Fazy 1 (Task 4, 6, 7).
from __future__ import annotations

import os

# Kaggle SDK does an auth check at module-import time. Tests mock the
# SDK entirely, but the import itself must not crash on developer
# machines without configured credentials. Set dummy values that the
# SDK accepts at import; tests never invoke real authentication.
os.environ.setdefault("KAGGLE_USERNAME", "test")
os.environ.setdefault("KAGGLE_KEY", "test")

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
