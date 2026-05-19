"""Testy endpointów REST nad widokami analitycznymi."""
from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient


def _view_count(conn: sqlite3.Connection, view: str, where: str = "") -> int:
    """Niezależny COUNT(*) dla weryfikacji pola ``total`` w odpowiedzi."""
    sql = f"SELECT COUNT(*) AS c FROM {view}"
    if where:
        sql += f" {where}"
    return int(conn.execute(sql).fetchone()[0])


# ---------- /api/views/top-rated-games --------------------------------------


def test_top_rated_games_returns_items_and_total(
    client: TestClient, views_conn: sqlite3.Connection
) -> None:
    res = client.get("/api/views/top-rated-games")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)
    assert body["total"] == _view_count(views_conn, "vw_top_rated_games")


def test_top_rated_games_pagination_limit_offset(client: TestClient) -> None:
    res = client.get("/api/views/top-rated-games", params={"limit": 2, "offset": 1})
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) <= 2


def test_top_rated_games_rejects_invalid_limit(client: TestClient) -> None:
    res = client.get("/api/views/top-rated-games", params={"limit": 999})
    assert res.status_code == 422


# ---------- /api/views/genre-stats ------------------------------------------


def test_genre_stats_returns_items_and_total(
    client: TestClient, views_conn: sqlite3.Connection
) -> None:
    res = client.get("/api/views/genre-stats")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)
    assert body["total"] == _view_count(views_conn, "vw_genre_stats")
    assert body["total"] == len(body["items"])


# ---------- /api/views/developer-leaderboard --------------------------------


def test_developer_leaderboard_returns_items_and_total(
    client: TestClient, views_conn: sqlite3.Connection
) -> None:
    res = client.get("/api/views/developer-leaderboard")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)
    assert body["total"] == _view_count(views_conn, "vw_developer_leaderboard")


def test_developer_leaderboard_pagination_limit_offset(client: TestClient) -> None:
    res = client.get("/api/views/developer-leaderboard", params={"limit": 2, "offset": 1})
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) <= 2


def test_developer_leaderboard_rejects_invalid_limit(client: TestClient) -> None:
    res = client.get("/api/views/developer-leaderboard", params={"limit": 999})
    assert res.status_code == 422


# ---------- /api/views/price-range-distribution -----------------------------


def test_price_range_distribution_returns_items_and_total(
    client: TestClient, views_conn: sqlite3.Connection
) -> None:
    res = client.get("/api/views/price-range-distribution")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)
    assert body["total"] == _view_count(views_conn, "vw_price_range_distribution")
    assert body["total"] == len(body["items"])


# ---------- /api/views/sentiment-per-genre ----------------------------------


def test_sentiment_per_genre_returns_items_and_total(
    client: TestClient, views_conn: sqlite3.Connection
) -> None:
    res = client.get("/api/views/sentiment-per-genre")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)
    assert body["total"] == _view_count(views_conn, "vw_sentiment_per_genre")
    assert body["total"] == len(body["items"])


# ---------- /api/views/monthly-releases -------------------------------------


def test_monthly_releases_returns_items_and_total(
    client: TestClient, views_conn: sqlite3.Connection
) -> None:
    res = client.get("/api/views/monthly-releases")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)
    assert body["total"] == _view_count(views_conn, "vw_monthly_releases")
    assert body["total"] == len(body["items"])


def test_monthly_releases_year_filter_lower_bound(client: TestClient) -> None:
    res = client.get("/api/views/monthly-releases", params={"year_from": 2099})
    assert res.status_code == 200
    body = res.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_monthly_releases_year_filter_inclusive(
    client: TestClient, views_conn: sqlite3.Connection
) -> None:
    """Filtrowanie z włączeniem znanego roku zwraca dokładnie wiersze tego roku."""
    # Wybieramy pierwszy rok obecny w widoku (fixture stale ma min. jeden).
    row = views_conn.execute(
        "SELECT year FROM vw_monthly_releases ORDER BY year ASC LIMIT 1"
    ).fetchone()
    assert row is not None, "Fixture views_conn powinien zawierać przynajmniej jeden rok premier."
    known_year = int(row[0])

    res = client.get(
        "/api/views/monthly-releases",
        params={"year_from": known_year, "year_to": known_year},
    )
    assert res.status_code == 200
    body = res.json()
    expected = _view_count(
        views_conn,
        "vw_monthly_releases",
        where=f"WHERE year = {known_year}",
    )
    assert body["total"] == expected
    assert len(body["items"]) == expected
    assert all(item["year"] == known_year for item in body["items"])


# ---------- OpenAPI ---------------------------------------------------------


def test_view_endpoints_are_in_openapi(client: TestClient) -> None:
    res = client.get("/openapi.json")
    assert res.status_code == 200
    paths = res.json()["paths"]
    for expected in (
        "/api/views/top-rated-games",
        "/api/views/genre-stats",
        "/api/views/developer-leaderboard",
        "/api/views/price-range-distribution",
        "/api/views/sentiment-per-genre",
        "/api/views/monthly-releases",
    ):
        assert expected in paths, f"Brak {expected} w schemacie OpenAPI"
