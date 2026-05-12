"""Ładowanie tabel wymiarów hurtowni.

Każda funkcja `_load_<dim>` jest idempotentna (`INSERT OR IGNORE` + UNIQUE),
po zakończeniu odczytuje cały wymiar i zwraca lookup map (naturalny klucz → klucz surogatowy).
`load_all_dimensions(conn)` orkiestruje wszystkie wymiary i zwraca słownik map.
"""
from __future__ import annotations

import logging
import sqlite3

import pandas as pd

from backend.etl.parsers import classify_developer, release_date_to_period
from backend.etl.sentiment import SENTIMENT_BUCKETS

logger = logging.getLogger(__name__)


def _genre_names(conn: sqlite3.Connection) -> set[str]:
    """Zbiera unikalne nazwy gatunków ze stg_kaggle + stg_steam_api."""
    genres: set[str] = set()
    for table, col in [("stg_kaggle", "genres"), ("stg_steam_api", "genres")]:
        try:
            df = pd.read_sql(f"SELECT {col} FROM {table}", conn)
        except pd.errors.DatabaseError:
            continue
        for cell in df[col].dropna():
            for g in str(cell).split(","):
                g = g.strip()
                if g:
                    genres.add(g)
    return genres


def _load_dim_genre(conn: sqlite3.Connection) -> dict[str, int]:
    for name in sorted(_genre_names(conn)):
        conn.execute("INSERT OR IGNORE INTO dim_genre (name) VALUES (?)", (name,))
    conn.commit()
    return dict(conn.execute("SELECT name, genre_key FROM dim_genre").fetchall())


def _developer_counts(conn: sqlite3.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    try:
        df = pd.read_sql("SELECT developers FROM stg_kaggle WHERE developers IS NOT NULL", conn)
    except pd.errors.DatabaseError:
        return counts
    for cell in df["developers"]:
        for dev in str(cell).split(","):
            dev = dev.strip()
            if dev:
                counts[dev] = counts.get(dev, 0) + 1
    return counts


def _load_dim_developer(conn: sqlite3.Connection) -> dict[str, int]:
    """Ładuje dim_developer. Re-run aktualizuje games_count i developer_class
    (UPSERT), zachowując developer_key dla istniejących wpisów (FK-safe)."""
    for name, count in _developer_counts(conn).items():
        conn.execute(
            """
            INSERT INTO dim_developer (name, games_count, developer_class)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                games_count = excluded.games_count,
                developer_class = excluded.developer_class
            """,
            (name, count, classify_developer(count)),
        )
    conn.commit()
    return dict(conn.execute("SELECT name, developer_key FROM dim_developer").fetchall())


_PLATFORMS = ("Windows", "Mac", "Linux")


def _load_dim_platform(conn: sqlite3.Connection) -> dict[str, int]:
    for p in _PLATFORMS:
        conn.execute("INSERT OR IGNORE INTO dim_platform (name) VALUES (?)", (p,))
    conn.commit()
    return dict(conn.execute("SELECT name, platform_key FROM dim_platform").fetchall())


_PRICE_RANGES = [
    ("Free", 0.0, 0.0),
    ("$0.01-4.99", 0.01, 4.99),
    ("$5-14.99", 5.00, 14.99),
    ("$15-29.99", 15.00, 29.99),
    ("$30-59.99", 30.00, 59.99),
    ("$60+", 60.00, None),
]


def _load_dim_price_range(conn: sqlite3.Connection) -> dict[str, int]:
    for label, lo, hi in _PRICE_RANGES:
        conn.execute(
            "INSERT OR IGNORE INTO dim_price_range (label, min_price, max_price) VALUES (?, ?, ?)",
            (label, lo, hi),
        )
    conn.commit()
    return dict(conn.execute("SELECT label, price_range_key FROM dim_price_range").fetchall())


def _load_dim_sentiment(conn: sqlite3.Connection) -> dict[str, int]:
    for bucket in SENTIMENT_BUCKETS:
        conn.execute(
            "INSERT OR IGNORE INTO dim_sentiment (label, score_min, score_max) VALUES (?, ?, ?)",
            (bucket["label"], bucket["score_min"], bucket["score_max"]),
        )
    conn.commit()
    return dict(conn.execute("SELECT label, sentiment_key FROM dim_sentiment").fetchall())


def _load_dim_release_period(conn: sqlite3.Connection) -> dict[tuple[int, int], int]:
    try:
        df = pd.read_sql(
            "SELECT DISTINCT release_date FROM stg_kaggle WHERE release_date IS NOT NULL", conn
        )
    except pd.errors.DatabaseError:
        df = pd.DataFrame(columns=["release_date"])

    periods: set[tuple[int, int, int, str, str]] = set()
    for raw in df["release_date"]:
        p = release_date_to_period(raw)
        if p is None:
            continue
        periods.add((p["year"], p["quarter"], p["month"], p["month_name"], p["season"]))

    for year, quarter, month, month_name, season in sorted(periods):
        conn.execute(
            "INSERT OR IGNORE INTO dim_release_period (year, quarter, month, month_name, season) VALUES (?, ?, ?, ?, ?)",
            (year, quarter, month, month_name, season),
        )
    conn.commit()

    cur = conn.execute("SELECT year, month, release_period_key FROM dim_release_period")
    return {(int(y), int(m)): int(k) for y, m, k in cur.fetchall()}


def load_all_dimensions(conn: sqlite3.Connection) -> dict[str, dict]:
    """Ładuje wszystkie wymiary i zwraca słownik lookup-map.

    Klucze: 'genre', 'developer', 'platform', 'price_range', 'release_period', 'sentiment'.
    """
    return {
        "genre": _load_dim_genre(conn),
        "developer": _load_dim_developer(conn),
        "platform": _load_dim_platform(conn),
        "price_range": _load_dim_price_range(conn),
        "release_period": _load_dim_release_period(conn),
        "sentiment": _load_dim_sentiment(conn),
    }
