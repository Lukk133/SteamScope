"""Testy ładowania wszystkich wymiarów."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backend.etl.load_dimensions import load_all_dimensions
from backend.etl.staging import stage_kaggle, stage_steam_api, stage_steamspy
from backend.warehouse.connection import connect, init_schema

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def populated_conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    init_schema(conn)
    stage_kaggle(FIXTURES / "etl_sample_kaggle.csv", conn)
    stage_steam_api(FIXTURES / "etl_sample_steam_api", conn)
    stage_steamspy(FIXTURES / "etl_sample_steamspy", conn)
    yield conn
    conn.close()


def test_load_returns_lookup_maps(populated_conn) -> None:
    maps = load_all_dimensions(populated_conn)
    assert set(maps.keys()) == {
        "genre", "developer", "platform", "price_range",
        "release_period", "sentiment",
    }


def test_dim_genre_populated(populated_conn) -> None:
    load_all_dimensions(populated_conn)
    df = pd.read_sql("SELECT name FROM dim_genre", populated_conn)
    names = set(df["name"])
    assert {"Action", "Shooter", "Adventure", "Puzzle", "Indie"}.issubset(names)


def test_dim_developer_has_classification(populated_conn) -> None:
    load_all_dimensions(populated_conn)
    df = pd.read_sql(
        "SELECT name, games_count, developer_class FROM dim_developer",
        populated_conn,
    )
    valve = df[df["name"] == "Valve"].iloc[0]
    assert int(valve["games_count"]) == 4
    assert valve["developer_class"] == "AA"
    indie = df[df["name"] == "IndieDev"].iloc[0]
    assert indie["developer_class"] == "indie"


def test_dim_platform_has_three_rows(populated_conn) -> None:
    load_all_dimensions(populated_conn)
    df = pd.read_sql("SELECT name FROM dim_platform", populated_conn)
    assert set(df["name"]) == {"Windows", "Mac", "Linux"}


def test_dim_price_range_has_six_rows(populated_conn) -> None:
    load_all_dimensions(populated_conn)
    df = pd.read_sql("SELECT label FROM dim_price_range", populated_conn)
    assert set(df["label"]) == {
        "Free", "$0.01-4.99", "$5-14.99", "$15-29.99", "$30-59.99", "$60+",
    }


def test_dim_sentiment_has_five_rows(populated_conn) -> None:
    load_all_dimensions(populated_conn)
    df = pd.read_sql("SELECT label FROM dim_sentiment", populated_conn)
    assert set(df["label"]) == {
        "Very Negative", "Negative", "Mixed", "Positive", "Very Positive",
    }


def test_dim_release_period_built_from_games(populated_conn) -> None:
    load_all_dimensions(populated_conn)
    df = pd.read_sql("SELECT year, month, season FROM dim_release_period", populated_conn)
    pairs = sorted({(int(y), int(m)) for y, m in zip(df["year"], df["month"])})
    assert (1998, 11) in pairs
    assert (2007, 10) in pairs


def test_load_is_idempotent(populated_conn) -> None:
    maps1 = load_all_dimensions(populated_conn)
    rows_before = pd.read_sql("SELECT COUNT(*) AS c FROM dim_genre", populated_conn).iloc[0]["c"]
    load_all_dimensions(populated_conn)
    rows_after = pd.read_sql("SELECT COUNT(*) AS c FROM dim_genre", populated_conn).iloc[0]["c"]
    assert rows_before == rows_after
    maps2 = load_all_dimensions(populated_conn)
    assert maps1["genre"] == maps2["genre"]


def test_dim_developer_upsert_refreshes_counts(tmp_path) -> None:
    """When staging data changes between runs, developer counts must refresh
    while developer_key stays stable (FK-preserving)."""
    from backend.warehouse.connection import connect, init_schema

    conn = connect(tmp_path / "test.db")
    init_schema(conn)
    # Initial load: IndieDev appears once
    pd.DataFrame([{"appid": 1, "developers": "IndieDev"}]).to_sql(
        "stg_kaggle", conn, if_exists="replace", index=False,
    )
    maps1 = load_all_dimensions(conn)
    key1 = maps1["developer"]["IndieDev"]
    row1 = conn.execute(
        "SELECT games_count, developer_class FROM dim_developer WHERE name = 'IndieDev'"
    ).fetchone()
    assert row1 == (1, "indie")

    # Re-run with 5 games: classification should bump to AA
    pd.DataFrame(
        [{"appid": i, "developers": "IndieDev"} for i in range(1, 6)]
    ).to_sql("stg_kaggle", conn, if_exists="replace", index=False)
    maps2 = load_all_dimensions(conn)
    key2 = maps2["developer"]["IndieDev"]
    row2 = conn.execute(
        "SELECT games_count, developer_class FROM dim_developer WHERE name = 'IndieDev'"
    ).fetchone()
    assert row2 == (5, "AA")
    # Key must be stable for FK preservation
    assert key1 == key2
    conn.close()
