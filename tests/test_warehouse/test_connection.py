"""Testy modułu połączenia i inicjalizacji schematu hurtowni."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from backend.warehouse.connection import connect, init_schema


def _table_names(conn: sqlite3.Connection) -> set[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    return {row[0] for row in cur.fetchall()}


def _index_names(conn: sqlite3.Connection) -> set[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
    )
    return {row[0] for row in cur.fetchall()}


def test_connect_returns_sqlite_connection(tmp_path: Path) -> None:
    conn = connect(tmp_path / "wh.db")
    assert isinstance(conn, sqlite3.Connection)
    conn.close()


def test_connect_enables_foreign_keys(tmp_path: Path) -> None:
    conn = connect(tmp_path / "wh.db")
    fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1
    conn.close()


def test_init_schema_creates_all_tables(tmp_path: Path) -> None:
    conn = connect(tmp_path / "wh.db")
    init_schema(conn)
    tables = _table_names(conn)
    expected = {
        "dim_genre", "dim_developer", "dim_platform", "dim_price_range",
        "dim_release_period", "dim_sentiment", "dim_date",
        "fact_games", "fact_reviews",
        "bridge_game_genre", "bridge_game_platform",
    }
    assert expected.issubset(tables), f"missing: {expected - tables}"
    conn.close()


def test_init_schema_creates_indexes(tmp_path: Path) -> None:
    conn = connect(tmp_path / "wh.db")
    init_schema(conn)
    indexes = _index_names(conn)
    expected = {
        "ix_fact_games_genre", "ix_fact_games_developer",
        "ix_fact_games_price_range", "ix_fact_games_release_date",
        "ix_fact_games_rating", "ix_fact_reviews_game",
    }
    assert expected.issubset(indexes), f"missing: {expected - indexes}"
    conn.close()


def test_init_schema_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "wh.db"
    conn1 = connect(db)
    init_schema(conn1)
    conn1.close()

    conn2 = connect(db)
    init_schema(conn2)  # must not raise
    tables = _table_names(conn2)
    assert "fact_games" in tables
    conn2.close()


def test_fact_games_has_expected_columns(tmp_path: Path) -> None:
    conn = connect(tmp_path / "wh.db")
    init_schema(conn)
    cur = conn.execute("PRAGMA table_info(fact_games)")
    cols = {row[1] for row in cur.fetchall()}
    expected = {
        "game_id", "name", "genre_key", "developer_key", "price_range_key",
        "release_period_key", "sentiment_key", "price_usd", "rating_score",
        "review_count", "positive_review_count", "negative_review_count",
        "estimated_owners", "estimated_revenue_usd", "release_date",
        "playtime_avg_hours",
    }
    assert expected == cols
    conn.close()
