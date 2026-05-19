"""Testy podstawowych endpointów: /, /api/health."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_root_returns_metadata() -> None:
    res = _client().get("/")
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "SteamScope API"
    assert body["docs"] == "/docs"


def test_health_returns_ok() -> None:
    res = _client().get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_openapi_schema_is_published() -> None:
    res = _client().get("/openapi.json")
    assert res.status_code == 200
    schema = res.json()
    assert schema["info"]["title"] == "SteamScope API"
    assert schema["info"]["version"] == "0.1.0"


def test_cors_headers_present_on_preflight() -> None:
    res = _client().options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
