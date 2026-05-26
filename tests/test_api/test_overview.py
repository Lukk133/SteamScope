"""Testy endpointu zbiorczego KPI /api/overview."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_overview_returns_kpi_object(client: TestClient) -> None:
    res = client.get("/api/overview")
    assert res.status_code == 200
    body = res.json()
    for key in (
        "total_games",
        "total_developers",
        "total_genres",
        "avg_rating",
        "avg_price_usd",
        "total_estimated_owners",
        "total_reviews",
        "total_estimated_revenue_usd",
    ):
        assert key in body, f"Brak klucza {key} w odpowiedzi /api/overview"
    assert isinstance(body["total_games"], int)
    assert body["total_games"] >= 1


def test_overview_in_openapi(client: TestClient) -> None:
    res = client.get("/openapi.json")
    assert res.status_code == 200
    assert "/api/overview" in res.json()["paths"]
