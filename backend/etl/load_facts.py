"""Ładowanie tabel faktów i pomostowych.

Wymaga, by wymiary były już załadowane (przekazane jako `maps`).
"""
from __future__ import annotations

import hashlib
import logging
import sqlite3

import pandas as pd

from backend.etl.parsers import price_to_range_label, release_date_to_period
from backend.etl.sentiment import aggregate_per_game, compound_to_label, score_review

logger = logging.getLogger(__name__)


def _read_staged_games(conn: sqlite3.Connection) -> pd.DataFrame:
    """Buduje DataFrame z połączonych stg_kaggle + stg_steam_api + stg_steamspy."""
    kaggle = pd.read_sql("SELECT * FROM stg_kaggle", conn)
    try:
        steam = pd.read_sql("SELECT * FROM stg_steam_api", conn)
    except pd.errors.DatabaseError:
        steam = pd.DataFrame(columns=["appid"])
    try:
        spy = pd.read_sql("SELECT * FROM stg_steamspy", conn)
    except pd.errors.DatabaseError:
        spy = pd.DataFrame(columns=["appid"])

    df = kaggle.merge(
        steam[[c for c in steam.columns if c == "appid" or c.startswith(("genres", "categories", "release_date", "price_usd", "windows", "mac", "linux"))]],
        on="appid", how="left", suffixes=("", "_api"),
    )
    spy_cols = spy[["appid", "estimated_owners", "average_forever_minutes"]].rename(
        columns={"estimated_owners": "estimated_owners_spy"}
    )
    df = df.merge(spy_cols, on="appid", how="left")
    # Prefer steamspy integer midpoint over kaggle raw string
    df["estimated_owners"] = df["estimated_owners_spy"]
    return df


def _primary_developer(devs_csv: str | None) -> str | None:
    if not devs_csv or not isinstance(devs_csv, str):
        return None
    return devs_csv.split(",")[0].strip() or None


def _primary_genre(genres_csv: str | None) -> str | None:
    if not genres_csv or not isinstance(genres_csv, str):
        return None
    return genres_csv.split(",")[0].strip() or None


def load_fact_games(conn: sqlite3.Connection, maps: dict[str, dict]) -> int:
    """Ładuje fact_games. Zwraca liczbę wstawionych/podmienionych wierszy."""
    df = _read_staged_games(conn)

    try:
        reviews_df = pd.read_sql("SELECT appid, review_text FROM stg_reviews", conn)
    except pd.errors.DatabaseError:
        reviews_df = pd.DataFrame(columns=["appid", "review_text"])
    sentiment = aggregate_per_game(reviews_df)
    df = df.merge(sentiment, on="appid", how="left")

    rows: list[tuple] = []
    for _, r in df.iterrows():
        appid = int(r["appid"])
        name = str(r.get("name") or f"appid_{appid}")
        price = float(r.get("price") or 0.0)
        owners = int(r["estimated_owners"]) if pd.notna(r.get("estimated_owners")) else None
        revenue = float(owners) * price if owners is not None else None
        positive = int(r["positive"]) if pd.notna(r.get("positive")) else None
        negative = int(r["negative"]) if pd.notna(r.get("negative")) else None
        total = (positive or 0) + (negative or 0)
        rating = (positive / total * 100.0) if total > 0 else None
        playtime = (
            float(r["average_forever_minutes"]) / 60.0
            if pd.notna(r.get("average_forever_minutes")) else None
        )

        primary_genre = _primary_genre(r.get("genres"))
        genre_key = maps["genre"].get(primary_genre) if primary_genre else None

        primary_dev = _primary_developer(r.get("developers"))
        dev_key = maps["developer"].get(primary_dev) if primary_dev else None

        price_label = price_to_range_label(price)
        price_range_key = maps["price_range"][price_label]

        period = release_date_to_period(r.get("release_date"))
        period_key = (
            maps["release_period"].get((period["year"], period["month"]))
            if period else None
        )

        sentiment_label = r.get("sentiment_label")
        sentiment_key = maps["sentiment"].get(sentiment_label) if isinstance(sentiment_label, str) else None

        rows.append((
            appid, name, genre_key, dev_key, price_range_key, period_key, sentiment_key,
            price, rating, total, positive, negative,
            owners, revenue, r.get("release_date"), playtime,
        ))

    conn.executemany(
        """
        INSERT OR REPLACE INTO fact_games (
            game_id, name, genre_key, developer_key, price_range_key,
            release_period_key, sentiment_key, price_usd, rating_score,
            review_count, positive_review_count, negative_review_count,
            estimated_owners, estimated_revenue_usd, release_date, playtime_avg_hours
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def load_bridges(conn: sqlite3.Connection, maps: dict[str, dict]) -> dict[str, int]:
    """Ładuje bridge_game_genre i bridge_game_platform z stg_kaggle + stg_steam_api."""
    bg_count = 0
    sources = [("stg_kaggle", "genres"), ("stg_steam_api", "genres")]
    seen: set[tuple[int, int]] = set()
    for tbl, col in sources:
        try:
            df = pd.read_sql(f"SELECT appid, {col} FROM {tbl}", conn)
        except pd.errors.DatabaseError:
            continue
        for _, r in df.iterrows():
            if not isinstance(r[col], str):
                continue
            for g in r[col].split(","):
                g = g.strip()
                if not g:
                    continue
                gkey = maps["genre"].get(g)
                if gkey is None:
                    continue
                key = (int(r["appid"]), gkey)
                if key in seen:
                    continue
                seen.add(key)
                conn.execute(
                    "INSERT OR IGNORE INTO bridge_game_genre (game_id, genre_key) VALUES (?, ?)",
                    key,
                )
                bg_count += 1

    bp_count = 0
    try:
        df = pd.read_sql("SELECT appid, windows, mac, linux FROM stg_kaggle", conn)
    except pd.errors.DatabaseError:
        df = pd.DataFrame()
    for _, r in df.iterrows():
        for platform_col, platform_name in (("windows", "Windows"), ("mac", "Mac"), ("linux", "Linux")):
            if int(r.get(platform_col) or 0) == 1:
                pkey = maps["platform"][platform_name]
                conn.execute(
                    "INSERT OR IGNORE INTO bridge_game_platform (game_id, platform_key) VALUES (?, ?)",
                    (int(r["appid"]), pkey),
                )
                bp_count += 1

    conn.commit()
    return {"bridge_game_genre": bg_count, "bridge_game_platform": bp_count}


def _review_id(game_id: int, author: str | None, posted_date: str | None) -> str:
    """Deterministyczny hash dla recenzji."""
    payload = f"{game_id}|{author or ''}|{posted_date or ''}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def load_fact_reviews(conn: sqlite3.Connection, maps: dict[str, dict]) -> int:
    """Ładuje fact_reviews z stg_reviews + sentymentu per recenzja."""
    try:
        df = pd.read_sql("SELECT * FROM stg_reviews", conn)
    except pd.errors.DatabaseError:
        return 0
    rows: list[tuple] = []
    sentiment_map = maps["sentiment"]
    for _, r in df.iterrows():
        compound = score_review(r.get("review_text"))
        label = compound_to_label(compound)
        rows.append((
            _review_id(int(r["appid"]), r.get("author"), r.get("posted_date")),
            int(r["appid"]),
            None,  # review_date_key — Phase 3 will build dim_date
            compound,
            sentiment_map.get(label),
            int(r["helpful_count"]) if pd.notna(r.get("helpful_count")) else None,
            float(r["playtime_hours"]) if pd.notna(r.get("playtime_hours")) else None,
            int(r["voted_up"]) if pd.notna(r.get("voted_up")) else 0,
        ))
    conn.executemany(
        """
        INSERT OR REPLACE INTO fact_reviews (
            review_id, game_id, review_date_key, sentiment_score,
            sentiment_label_key, helpful_count, playtime_at_review_hours, voted_up
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)
