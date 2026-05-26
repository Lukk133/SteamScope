"""Testy widoków analitycznych warstwy wynikowej."""
from __future__ import annotations

import pandas as pd

from backend.etl.load_dimensions import _PRICE_RANGES
from backend.etl.sentiment import SENTIMENT_BUCKETS
from backend.warehouse.connection import init_views


def test_vw_top_rated_games_returns_rows_with_min_reviews(views_conn) -> None:
    df = pd.read_sql("SELECT * FROM vw_top_rated_games", views_conn)
    # Każdy zwrócony wiersz musi spełniać próg ≥ 10 recenzji i mieć nazwę.
    assert (df["review_count"] >= 10).all()
    assert df["name"].notna().all()
    assert (df["name"].astype(str).str.len() > 0).all()
    # Ranking malejący po rating_score.
    ratings = df["rating_score"].tolist()
    assert ratings == sorted(ratings, reverse=True)


def test_vw_genre_stats_aggregates_per_genre(views_conn) -> None:
    df = pd.read_sql("SELECT * FROM vw_genre_stats", views_conn)
    assert len(df) >= 1
    assert df["genre"].notna().all()
    assert (df["games_count"] >= 1).all()
    valid_rating = df["avg_rating"].dropna()
    assert ((valid_rating >= 0) & (valid_rating <= 100)).all()


def test_vw_developer_leaderboard_returns_class(views_conn) -> None:
    df = pd.read_sql("SELECT * FROM vw_developer_leaderboard", views_conn)
    assert len(df) >= 1
    assert df["developer_class"].isin({"indie", "AA", "AAA"}).all()
    # games_count w widoku powinien zgadzać się z liczbą wierszy w fact_games per developer.
    actual = pd.read_sql(
        """
        SELECT d.name AS developer, COUNT(f.game_id) AS actual_count
        FROM fact_games f
        JOIN dim_developer d ON f.developer_key = d.developer_key
        GROUP BY d.name
        """,
        views_conn,
    )
    merged = df.merge(actual, on="developer", how="left")
    assert (merged["games_count"] == merged["actual_count"]).all()


def test_vw_price_range_distribution_covers_all_buckets(views_conn) -> None:
    df = pd.read_sql("SELECT * FROM vw_price_range_distribution", views_conn)
    known_labels = {label for label, _, _ in _PRICE_RANGES}
    # Spec: 0-game bucket nie pojawia się (INNER JOIN z fact_games). Sprawdzamy podzbiór.
    assert set(df["price_range_label"]).issubset(known_labels)
    assert (df["games_count"] >= 1).all()
    # Sortowanie rosnące po min_price.
    min_prices = df["min_price"].tolist()
    assert min_prices == sorted(min_prices)


def test_vw_sentiment_per_genre_pairs_dim_values(views_conn) -> None:
    df = pd.read_sql("SELECT * FROM vw_sentiment_per_genre", views_conn)
    sentiment_labels = {b["label"] for b in SENTIMENT_BUCKETS}
    assert df["sentiment_label"].isin(sentiment_labels).all()
    assert df["genre"].notna().all()
    assert (df["games_count"] >= 1).all()


def test_vw_monthly_releases_returns_ordered_periods(views_conn) -> None:
    df = pd.read_sql("SELECT * FROM vw_monthly_releases", views_conn)
    assert len(df) >= 1
    assert (df["games_count"] >= 1).all()
    pairs = list(zip(df["year"].tolist(), df["month"].tolist(), strict=True))
    assert pairs == sorted(pairs)


def test_init_views_is_idempotent(views_conn) -> None:
    # Drugie wywołanie nie powinno rzucać błędu (DROP + CREATE).
    init_views(views_conn)
    init_views(views_conn)
    # Widoki nadal istnieją.
    names = {
        row[0]
        for row in views_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='view'"
        ).fetchall()
    }
    expected = {
        "vw_top_rated_games",
        "vw_genre_stats",
        "vw_developer_leaderboard",
        "vw_price_range_distribution",
        "vw_sentiment_per_genre",
        "vw_monthly_releases",
    }
    assert expected.issubset(names)


def test_vw_overview_returns_single_row_with_kpis(views_conn) -> None:
    df = pd.read_sql("SELECT * FROM vw_overview", views_conn)
    assert len(df) == 1
    expected_cols = {
        "total_games",
        "total_developers",
        "total_genres",
        "avg_rating",
        "avg_price_usd",
        "total_estimated_owners",
        "total_reviews",
        "total_estimated_revenue_usd",
    }
    assert expected_cols.issubset(set(df.columns))
    # Hurtownia z fixture ma co najmniej jedną grę i jeden gatunek.
    assert int(df["total_games"].iloc[0]) >= 1
    assert int(df["total_genres"].iloc[0]) >= 1


def test_init_views_refreshes_definition_on_change(views_conn) -> None:
    # Symulujemy lokalną podmianę definicji widoku (np. ręczną edycję
    # w trakcie developmentu) i sprawdzamy, że init_views przywraca
    # kanoniczną definicję z views.sql, a nie zachowuje "starej" wersji.
    views_conn.executescript(
        """
        DROP VIEW vw_genre_stats;
        CREATE VIEW vw_genre_stats AS SELECT 999 AS sentinel;
        """
    )
    views_conn.commit()

    # Sanity check: widok ma teraz fałszywą definicję z kolumną `sentinel`.
    fake_cols = {row[1] for row in views_conn.execute("PRAGMA table_info(vw_genre_stats)")}
    assert fake_cols == {"sentinel"}

    # Ponowne uruchomienie init_views powinno odtworzyć widok od zera.
    init_views(views_conn)

    cols = {row[1] for row in views_conn.execute("PRAGMA table_info(vw_genre_stats)")}
    # Sentinel zniknął — widok wrócił do kanonicznych kolumn z views.sql.
    assert "sentinel" not in cols
    assert {"genre", "games_count", "avg_rating"}.issubset(cols)
