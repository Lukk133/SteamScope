"""Testy klienta SteamSpy."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import responses

from backend.ingestion import fetch_steamspy
from backend.ingestion.fetch_steamspy import (
    STEAMSPY_API_URL,
    SteamSpyError,
    fetch_app_details,
    fetch_many,
)


@responses.activate
def test_fetch_app_details_returns_payload(sample_steamspy_payload: dict) -> None:
    responses.add(responses.GET, STEAMSPY_API_URL, json=sample_steamspy_payload, status=200)
    result = fetch_app_details(appid=70)
    assert result["name"] == "Half-Life"
    assert result["owners"].startswith("5,000,000")


@responses.activate
def test_fetch_app_details_raises_on_http_error() -> None:
    responses.add(responses.GET, STEAMSPY_API_URL, json={}, status=503)
    with pytest.raises(SteamSpyError):
        fetch_app_details(appid=70)


@responses.activate
def test_fetch_many_writes_and_skips(tmp_path: Path, sample_steamspy_payload: dict) -> None:
    responses.add(responses.GET, STEAMSPY_API_URL, json=sample_steamspy_payload, status=200)
    (tmp_path / "71.json").write_text('{"cached": true}', encoding="utf-8")

    with patch.object(fetch_steamspy, "time") as mock_time:
        mock_time.sleep = lambda *_: None
        statuses = fetch_many([70, 71], target_dir=tmp_path, rate_limit_seconds=0)

    assert statuses == {70: "fetched", 71: "skipped"}
    assert json.loads((tmp_path / "70.json").read_text(encoding="utf-8"))["name"] == "Half-Life"
    assert (tmp_path / "71.json").read_text(encoding="utf-8") == '{"cached": true}'


@responses.activate
def test_fetch_many_records_error(tmp_path: Path) -> None:
    responses.add(responses.GET, STEAMSPY_API_URL, json={}, status=500)
    with patch.object(fetch_steamspy, "time") as mock_time:
        mock_time.sleep = lambda *_: None
        statuses = fetch_many([70], target_dir=tmp_path, rate_limit_seconds=0)
    assert statuses == {70: "error"}
    assert not (tmp_path / "70.json").exists()
