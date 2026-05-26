"""Testy endpointów /api/games (lista, filtr, paginacja, szczegóły)."""
from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient


def test_list_games_returns_items_and_total(
    client: TestClient, views_conn: sqlite3.Connection
) -> None:
    res = client.get("/api/games")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)
    expected = int(views_conn.execute("SELECT COUNT(*) FROM vw_game_detail").fetchone()[0])
    assert body["total"] == expected
    if body["items"]:
        assert "game_id" in body["items"][0]
        assert "name" in body["items"][0]


def test_list_games_pagination(client: TestClient) -> None:
    res = client.get("/api/games", params={"limit": 1, "offset": 0})
    assert res.status_code == 200
    assert len(res.json()["items"]) <= 1


def test_list_games_rejects_invalid_limit(client: TestClient) -> None:
    res = client.get("/api/games", params={"limit": 999})
    assert res.status_code == 422


def test_list_games_filter_by_name(
    client: TestClient, views_conn: sqlite3.Connection
) -> None:
    row = views_conn.execute(
        "SELECT name FROM vw_game_detail WHERE name IS NOT NULL LIMIT 1"
    ).fetchone()
    assert row is not None
    name = row[0]
    fragment = name[: max(1, len(name) // 2)]
    res = client.get("/api/games", params={"q": fragment})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert all(fragment.lower() in item["name"].lower() for item in body["items"])


def test_game_detail_returns_full_record(
    client: TestClient, views_conn: sqlite3.Connection
) -> None:
    row = views_conn.execute("SELECT game_id FROM vw_game_detail LIMIT 1").fetchone()
    assert row is not None
    game_id = int(row[0])
    res = client.get(f"/api/games/{game_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["game_id"] == game_id
    assert "rating_score" in body
    assert "developer" in body


def test_game_detail_404_for_unknown_id(client: TestClient) -> None:
    res = client.get("/api/games/999999999")
    assert res.status_code == 404


def test_games_endpoints_in_openapi(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/games" in paths
    assert "/api/games/{game_id}" in paths
