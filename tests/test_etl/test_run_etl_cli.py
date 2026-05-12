"""Testy CLI orkiestrującego ETL."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from scripts import run_etl


@pytest.fixture(autouse=True)
def _no_real_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_etl, "_setup_logging", lambda: None)


def test_cli_schema_calls_init(tmp_path: Path) -> None:
    with patch.object(run_etl, "init_schema") as mock_init:
        exit_code = run_etl.main(["--step", "schema"])
    assert exit_code == 0
    mock_init.assert_called_once()


def test_cli_staging_calls_all_four_loaders() -> None:
    with (
        patch.object(run_etl, "init_schema"),
        patch.object(run_etl, "stage_kaggle") as mk,
        patch.object(run_etl, "stage_steam_api") as ms,
        patch.object(run_etl, "stage_steamspy") as msp,
        patch.object(run_etl, "stage_reviews") as mr,
    ):
        mk.return_value = 5
        ms.return_value = 2
        msp.return_value = 2
        mr.return_value = 4
        exit_code = run_etl.main(["--step", "staging"])
    assert exit_code == 0
    mk.assert_called_once()
    ms.assert_called_once()
    msp.assert_called_once()
    mr.assert_called_once()


def test_cli_dimensions_calls_loader() -> None:
    with (
        patch.object(run_etl, "init_schema"),
        patch.object(run_etl, "load_all_dimensions") as mock_dims,
    ):
        mock_dims.return_value = {"genre": {}, "developer": {}, "platform": {},
                                  "price_range": {}, "release_period": {}, "sentiment": {}}
        exit_code = run_etl.main(["--step", "dimensions"])
    assert exit_code == 0
    mock_dims.assert_called_once()


def test_cli_facts_calls_all_three() -> None:
    empty_maps = {"genre": {}, "developer": {}, "platform": {},
                  "price_range": {"Free": 1}, "release_period": {}, "sentiment": {}}
    with (
        patch.object(run_etl, "init_schema"),
        patch.object(run_etl, "load_all_dimensions", return_value=empty_maps),
        patch.object(run_etl, "load_fact_games", return_value=0) as mg,
        patch.object(run_etl, "load_bridges", return_value={"bridge_game_genre": 0, "bridge_game_platform": 0}) as mb,
        patch.object(run_etl, "load_fact_reviews", return_value=0) as mr,
    ):
        exit_code = run_etl.main(["--step", "facts"])
    assert exit_code == 0
    mg.assert_called_once()
    mb.assert_called_once()
    mr.assert_called_once()


def test_cli_all_runs_every_step() -> None:
    empty_maps = {"genre": {}, "developer": {}, "platform": {},
                  "price_range": {"Free": 1}, "release_period": {}, "sentiment": {}}
    with (
        patch.object(run_etl, "init_schema") as init,
        patch.object(run_etl, "stage_kaggle", return_value=0),
        patch.object(run_etl, "stage_steam_api", return_value=0),
        patch.object(run_etl, "stage_steamspy", return_value=0),
        patch.object(run_etl, "stage_reviews", return_value=0),
        patch.object(run_etl, "load_all_dimensions", return_value=empty_maps) as dims,
        patch.object(run_etl, "load_fact_games", return_value=0),
        patch.object(run_etl, "load_bridges", return_value={"bridge_game_genre": 0, "bridge_game_platform": 0}),
        patch.object(run_etl, "load_fact_reviews", return_value=0),
    ):
        exit_code = run_etl.main(["--step", "all"])
    assert exit_code == 0
    init.assert_called_once()
    dims.assert_called_once()


def test_cli_unknown_step_returns_error() -> None:
    with pytest.raises(SystemExit):
        run_etl.main(["--step", "bogus"])
