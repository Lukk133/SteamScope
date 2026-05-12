"""Testy klienta Steam Web API (single fetch). Sieć zmockowana przez `responses`."""
from __future__ import annotations

import json

import pytest
import requests
import responses

from backend.ingestion import fetch_steam_api
from backend.ingestion.fetch_steam_api import STEAM_API_URL, SteamAPIError, fetch_game_details


@responses.activate
def test_returns_data_on_success(sample_steam_api_payload: dict) -> None:
    responses.add(
        responses.GET,
        STEAM_API_URL,
        json=sample_steam_api_payload,
        status=200,
    )
    result = fetch_game_details(appid=70)
    assert result is not None
    assert result["name"] == "Half-Life"
    assert result["steam_appid"] == 70


@responses.activate
def test_returns_none_when_success_false() -> None:
    responses.add(
        responses.GET,
        STEAM_API_URL,
        json={"999999999": {"success": False}},
        status=200,
    )
    result = fetch_game_details(appid=999999999)
    assert result is None


@responses.activate
def test_raises_on_http_error() -> None:
    responses.add(
        responses.GET,
        STEAM_API_URL,
        json={"error": "rate limited"},
        status=429,
    )
    with pytest.raises(SteamAPIError):
        fetch_game_details(appid=70)


@responses.activate
def test_raises_on_network_error() -> None:
    responses.add(
        responses.GET,
        STEAM_API_URL,
        body=requests.ConnectionError("boom"),
    )
    with pytest.raises(SteamAPIError):
        fetch_game_details(appid=70)


@responses.activate
def test_raises_on_invalid_json() -> None:
    responses.add(
        responses.GET,
        STEAM_API_URL,
        body="<html>maintenance</html>",
        status=200,
        content_type="text/html",
    )
    with pytest.raises(SteamAPIError, match="invalid JSON"):
        fetch_game_details(appid=70)


@responses.activate
def test_uses_configured_user_agent() -> None:
    responses.add(
        responses.GET,
        STEAM_API_URL,
        json={"70": {"success": True, "data": {"name": "Half-Life"}}},
        status=200,
    )
    fetch_game_details(appid=70)
    assert "SteamAnalytics" in responses.calls[0].request.headers["User-Agent"]
