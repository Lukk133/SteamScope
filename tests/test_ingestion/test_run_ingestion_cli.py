"""Testy CLI orkiestrującego ingestion."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from scripts import run_ingestion


@pytest.fixture(autouse=True)
def _no_real_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent _setup_logging from touching real filesystem during tests."""
    monkeypatch.setattr(run_ingestion, "_setup_logging", lambda: None)


def test_parse_appids_from_string() -> None:
    assert run_ingestion._parse_appids("70,71, 72") == [70, 71, 72]
    assert run_ingestion._parse_appids("") == []
    assert run_ingestion._parse_appids("70") == [70]


def test_parse_appids_invalid_raises() -> None:
    with pytest.raises(ValueError):
        run_ingestion._parse_appids("not_a_number")


def test_cli_kaggle_calls_loader(tmp_path: Path) -> None:
    with patch.object(run_ingestion, "download_kaggle_dataset") as mock_loader:
        mock_loader.return_value = tmp_path / "games.csv"
        exit_code = run_ingestion.main(["--source", "kaggle"])
    assert exit_code == 0
    mock_loader.assert_called_once_with(force=False)


def test_cli_steam_calls_fetch_many() -> None:
    with patch.object(run_ingestion, "fetch_steam_api_many") as mock_fn:
        mock_fn.return_value = {70: "fetched", 71: "skipped"}
        exit_code = run_ingestion.main(["--source", "steam", "--appids", "70,71"])
    assert exit_code == 0
    mock_fn.assert_called_once_with(appids=[70, 71], force=False)


def test_cli_steam_requires_appids() -> None:
    exit_code = run_ingestion.main(["--source", "steam"])
    assert exit_code != 0


def test_cli_all_runs_every_step() -> None:
    with (
        patch.object(run_ingestion, "download_kaggle_dataset") as mock_kag,
        patch.object(run_ingestion, "fetch_steam_api_many") as mock_steam,
        patch.object(run_ingestion, "fetch_steamspy_many") as mock_spy,
        patch.object(run_ingestion, "scrape_reviews_many") as mock_scrape,
    ):
        mock_kag.return_value = Path("/tmp/games.csv")
        mock_steam.return_value = {70: "fetched"}
        mock_spy.return_value = {70: "fetched"}
        mock_scrape.return_value = {70: "fetched"}

        exit_code = run_ingestion.main(["--source", "all", "--appids", "70"])

    assert exit_code == 0
    mock_kag.assert_called_once()
    mock_steam.assert_called_once_with(appids=[70], force=False)
    mock_spy.assert_called_once_with(appids=[70], force=False)
    mock_scrape.assert_called_once_with(appids=[70], force=False)


def test_cli_force_flag_propagates() -> None:
    with patch.object(run_ingestion, "fetch_steam_api_many") as mock_fn:
        mock_fn.return_value = {}
        run_ingestion.main(["--source", "steam", "--appids", "70", "--force"])
    mock_fn.assert_called_once_with(appids=[70], force=True)


def test_cli_unknown_source_returns_error() -> None:
    with pytest.raises(SystemExit):
        run_ingestion.main(["--source", "bogus"])


def test_cli_all_force_propagates_to_every_step() -> None:
    with (
        patch.object(run_ingestion, "download_kaggle_dataset") as mock_kag,
        patch.object(run_ingestion, "fetch_steam_api_many") as mock_steam,
        patch.object(run_ingestion, "fetch_steamspy_many") as mock_spy,
        patch.object(run_ingestion, "scrape_reviews_many") as mock_scrape,
    ):
        mock_kag.return_value = Path("/tmp/games.csv")
        mock_steam.return_value = {70: "fetched"}
        mock_spy.return_value = {70: "fetched"}
        mock_scrape.return_value = {70: "fetched"}

        exit_code = run_ingestion.main(["--source", "all", "--appids", "70", "--force"])

    assert exit_code == 0
    mock_kag.assert_called_once_with(force=True)
    mock_steam.assert_called_once_with(appids=[70], force=True)
    mock_spy.assert_called_once_with(appids=[70], force=True)
    mock_scrape.assert_called_once_with(appids=[70], force=True)
