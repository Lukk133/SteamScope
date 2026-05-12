"""Testy ładowania faktów (games, reviews) i tabel pomostowych."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backend.etl.load_dimensions import load_all_dimensions
from backend.etl.load_facts import load_bridges, load_fact_games, load_fact_reviews
from backend.etl.staging import (
    stage_kaggle, stage_reviews, stage_steam_api, stage_steamspy,
)
from backend.warehouse.connection import connect, init_schema

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def loaded_conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    init_schema(conn)
    stage_kaggle(FIXTURES / "etl_sample_kaggle.csv", conn)
    stage_steam_api(FIXTURES / "etl_sample_steam_api", conn)
    stage_steamspy(FIXTURES / "etl_sample_steamspy", conn)
    stage_reviews(FIXTURES / "etl_sample_reviews", conn)
    yield conn
    conn.close()


def test_load_fact_games_inserts_one_row_per_appid(loaded_conn) -> None:
    maps = load_all_dimensions(loaded_conn)
    rows = load_fact_games(loaded_conn, maps)
    assert rows == 5
    df = pd.read_sql("SELECT game_id, name FROM fact_games ORDER BY game_id", loaded_conn)
    assert df["game_id"].tolist() == [70, 220, 400, 440, 9999998]


def test_load_fact_games_resolves_developer_fk(loaded_conn) -> None:
    maps = load_all_dimensions(loaded_conn)
    load_fact_games(loaded_conn, maps)
    df = pd.read_sql(
        """
        SELECT f.game_id, d.name AS dev_name, d.developer_class
        FROM fact_games f JOIN dim_developer d ON f.developer_key = d.developer_key
        WHERE f.game_id IN (70, 9999998)
        """,
        loaded_conn,
    )
    valve = df[df["game_id"] == 70].iloc[0]
    indie = df[df["game_id"] == 9999998].iloc[0]
    assert valve["dev_name"] == "Valve"
    assert valve["developer_class"] == "AA"
    assert indie["dev_name"] == "IndieDev"
    assert indie["developer_class"] == "indie"


def test_load_fact_games_computes_estimated_revenue(loaded_conn) -> None:
    maps = load_all_dimensions(loaded_conn)
    load_fact_games(loaded_conn, maps)
    df = pd.read_sql(
        "SELECT game_id, price_usd, estimated_owners, estimated_revenue_usd "
        "FROM fact_games WHERE game_id = 70",
        loaded_conn,
    )
    row = df.iloc[0]
    assert row["estimated_owners"] == 7_500_000
    assert row["estimated_revenue_usd"] == pytest.approx(7_500_000 * 9.99, rel=1e-3)


def test_load_fact_games_resolves_price_range(loaded_conn) -> None:
    maps = load_all_dimensions(loaded_conn)
    load_fact_games(loaded_conn, maps)
    df = pd.read_sql(
        """
        SELECT f.game_id, pr.label
        FROM fact_games f JOIN dim_price_range pr ON f.price_range_key = pr.price_range_key
        """,
        loaded_conn,
    )
    labels = dict(zip(df["game_id"], df["label"]))
    assert labels[70] == "$5-14.99"   # $9.99
    assert labels[440] == "Free"      # $0
    assert labels[9999998] == "$0.01-4.99"  # $4.99


def test_load_bridges_populates_many_to_many(loaded_conn) -> None:
    maps = load_all_dimensions(loaded_conn)
    load_fact_games(loaded_conn, maps)
    rows = load_bridges(loaded_conn, maps)
    bg = pd.read_sql(
        "SELECT COUNT(*) c FROM bridge_game_genre WHERE game_id = 70", loaded_conn
    ).iloc[0]["c"]
    bp = pd.read_sql(
        "SELECT COUNT(*) c FROM bridge_game_platform WHERE game_id = 70", loaded_conn
    ).iloc[0]["c"]
    assert bg >= 2
    assert bp == 3
    assert rows["bridge_game_genre"] >= bg
    assert rows["bridge_game_platform"] >= bp


def test_load_fact_reviews_inserts_rows(loaded_conn) -> None:
    maps = load_all_dimensions(loaded_conn)
    load_fact_games(loaded_conn, maps)
    rows = load_fact_reviews(loaded_conn, maps)
    assert rows == 4
    df = pd.read_sql(
        "SELECT review_id, game_id, sentiment_score, voted_up FROM fact_reviews "
        "ORDER BY game_id, review_id",
        loaded_conn,
    )
    assert len(df) == 4
    assert df["game_id"].tolist() == [70, 70, 220, 220]
    positive = df[df["game_id"] == 70].iloc[0]
    assert positive["sentiment_score"] > 0


def test_load_facts_idempotent(loaded_conn) -> None:
    maps = load_all_dimensions(loaded_conn)
    load_fact_games(loaded_conn, maps)
    load_bridges(loaded_conn, maps)
    load_fact_reviews(loaded_conn, maps)
    games_before = pd.read_sql("SELECT COUNT(*) c FROM fact_games", loaded_conn).iloc[0]["c"]
    reviews_before = pd.read_sql("SELECT COUNT(*) c FROM fact_reviews", loaded_conn).iloc[0]["c"]

    load_fact_games(loaded_conn, maps)
    load_bridges(loaded_conn, maps)
    load_fact_reviews(loaded_conn, maps)

    games_after = pd.read_sql("SELECT COUNT(*) c FROM fact_games", loaded_conn).iloc[0]["c"]
    reviews_after = pd.read_sql("SELECT COUNT(*) c FROM fact_reviews", loaded_conn).iloc[0]["c"]
    assert games_before == games_after
    assert reviews_before == reviews_after
