"""Testy klienta Steam Web API (single fetch). Sieć zmockowana przez `responses`."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
import responses

from backend.ingestion import fetch_steam_api
from backend.ingestion.fetch_steam_api import STEAM_API_URL, SteamAPIError, fetch_game_details, fetch_many


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


@responses.activate
def test_fetch_many_writes_files_and_returns_statuses(tmp_path: Path) -> None:
    responses.add(
        responses.GET, STEAM_API_URL,
        json={"70": {"success": True, "data": {"name": "Half-Life"}}}, status=200,
    )
    responses.add(
        responses.GET, STEAM_API_URL,
        json={"71": {"success": False}}, status=200,
    )

    with patch.object(fetch_steam_api, "time") as mock_time:
        mock_time.sleep = lambda *_: None  # no real sleeping
        statuses = fetch_many([70, 71], target_dir=tmp_path, rate_limit_seconds=0)

    assert statuses == {70: "fetched", 71: "missing"}
    assert (tmp_path / "70.json").exists()
    assert json.loads((tmp_path / "70.json").read_text(encoding="utf-8"))["name"] == "Half-Life"
    assert json.loads((tmp_path / "71.json").read_text(encoding="utf-8")) == {"_missing": True}


@responses.activate
def test_fetch_many_skips_existing_files(tmp_path: Path) -> None:
    (tmp_path / "70.json").write_text('{"already": true}', encoding="utf-8")

    statuses = fetch_many([70], target_dir=tmp_path, rate_limit_seconds=0, force=False)

    assert statuses == {70: "skipped"}
    assert len(responses.calls) == 0
    assert (tmp_path / "70.json").read_text(encoding="utf-8") == '{"already": true}'


@responses.activate
def test_fetch_many_force_overwrites(tmp_path: Path) -> None:
    (tmp_path / "70.json").write_text('{"old": true}', encoding="utf-8")
    responses.add(
        responses.GET, STEAM_API_URL,
        json={"70": {"success": True, "data": {"name": "Half-Life"}}}, status=200,
    )

    with patch.object(fetch_steam_api, "time") as mock_time:
        mock_time.sleep = lambda *_: None
        fetch_many([70], target_dir=tmp_path, rate_limit_seconds=0, force=True)

    assert json.loads((tmp_path / "70.json").read_text(encoding="utf-8"))["name"] == "Half-Life"


@responses.activate
def test_fetch_many_records_errors_without_crashing(tmp_path: Path) -> None:
    responses.add(responses.GET, STEAM_API_URL, json={}, status=500)

    with patch.object(fetch_steam_api, "time") as mock_time:
        mock_time.sleep = lambda *_: None
        statuses = fetch_many([70], target_dir=tmp_path, rate_limit_seconds=0)

    assert statuses == {70: "error"}
    assert not (tmp_path / "70.json").exists()


@responses.activate
def test_fetch_many_handles_disk_write_error(tmp_path: Path) -> None:
    responses.add(
        responses.GET, STEAM_API_URL,
        json={"70": {"success": True, "data": {"name": "Half-Life"}}}, status=200,
    )

    with patch.object(fetch_steam_api, "time") as mock_time, \
         patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
        mock_time.sleep = lambda *_: None
        statuses = fetch_many([70], target_dir=tmp_path, rate_limit_seconds=0)

    assert statuses == {70: "error"}
