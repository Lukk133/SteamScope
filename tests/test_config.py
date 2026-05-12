"""Testy modułu konfiguracji."""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.config import INGESTION, PATHS, IngestionConfig, Paths


def test_paths_derive_from_project_root(tmp_path: Path) -> None:
    paths = Paths(project_root=tmp_path)
    assert paths.data_dir == tmp_path / "data"
    assert paths.raw_dir == tmp_path / "data" / "raw"
    assert paths.kaggle_dir == tmp_path / "data" / "raw" / "kaggle"
    assert paths.steam_api_dir == tmp_path / "data" / "raw" / "steam_api"
    assert paths.steamspy_dir == tmp_path / "data" / "raw" / "steamspy"
    assert paths.scraped_dir == tmp_path / "data" / "raw" / "scraped"
    assert paths.processed_dir == tmp_path / "data" / "processed"
    assert paths.exports_dir == tmp_path / "data" / "exports"
    assert paths.db_dir == tmp_path / "db"
    assert paths.db_path == tmp_path / "db" / "steam_warehouse.db"
    assert paths.logs_dir == tmp_path / "logs"


def test_paths_ensure_creates_all_directories(tmp_path: Path) -> None:
    paths = Paths(project_root=tmp_path)
    paths.ensure()
    for attr in (
        "raw_dir", "processed_dir", "exports_dir",
        "kaggle_dir", "steam_api_dir", "steamspy_dir", "scraped_dir",
        "db_dir", "logs_dir",
    ):
        assert getattr(paths, attr).is_dir(), f"{attr} should exist"


def test_paths_is_frozen(tmp_path: Path) -> None:
    paths = Paths(project_root=tmp_path)
    with pytest.raises(Exception):  # FrozenInstanceError
        paths.project_root = tmp_path  # type: ignore[misc]


def test_ingestion_config_defaults() -> None:
    cfg = IngestionConfig()
    assert cfg.kaggle_csv_filename == "games.csv"
    assert cfg.steam_api_rate_limit_seconds >= 1.0
    assert cfg.steamspy_rate_limit_seconds >= 1.0
    assert cfg.steam_api_max_retries >= 1
    assert "SteamAnalytics" in cfg.user_agent


def test_module_level_singletons_exist() -> None:
    assert isinstance(PATHS, Paths)
    assert isinstance(INGESTION, IngestionConfig)
