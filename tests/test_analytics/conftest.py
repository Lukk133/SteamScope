"""Fixtury lokalne dla testów eksporterów warstwy analitycznej."""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.etl.load_dimensions import load_all_dimensions
from backend.etl.load_facts import load_bridges, load_fact_games, load_fact_reviews
from backend.etl.staging import (
    stage_kaggle,
    stage_reviews,
    stage_steam_api,
    stage_steamspy,
)
from backend.warehouse.connection import connect, init_schema, init_views

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def views_conn(tmp_path):
    """Tworzy hurtownię od zera, ładuje fakty i wymiary, inicjalizuje widoki."""
    conn = connect(tmp_path / "views.db")
    init_schema(conn)
    stage_kaggle(FIXTURES / "etl_sample_kaggle.csv", conn)
    stage_steam_api(FIXTURES / "etl_sample_steam_api", conn)
    stage_steamspy(FIXTURES / "etl_sample_steamspy", conn)
    stage_reviews(FIXTURES / "etl_sample_reviews", conn)
    maps = load_all_dimensions(conn)
    load_fact_games(conn, maps)
    load_bridges(conn, maps)
    load_fact_reviews(conn, maps)
    init_views(conn)
    yield conn
    conn.close()
