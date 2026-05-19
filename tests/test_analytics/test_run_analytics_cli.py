"""Testy CLI orkiestrującego warstwę analityczną."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from scripts import run_analytics


@pytest.fixture(autouse=True)
def _no_real_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_analytics, "_setup_logging", lambda: None)


def test_cli_views_calls_init_views() -> None:
    with (
        patch.object(run_analytics, "init_schema") as mock_schema,
        patch.object(run_analytics, "init_views") as mock_views,
    ):
        exit_code = run_analytics.main(["--step", "views"])
    assert exit_code == 0
    mock_schema.assert_called_once()
    mock_views.assert_called_once()


def test_cli_export_csv_calls_csv_exporter() -> None:
    with (
        patch.object(run_analytics, "init_schema"),
        patch.object(run_analytics, "init_views"),
        patch.object(run_analytics, "export_all_views_to_csv", return_value={}) as mock_csv,
    ):
        exit_code = run_analytics.main(["--step", "export-csv"])
    assert exit_code == 0
    mock_csv.assert_called_once()
    out_arg = mock_csv.call_args.args[1]
    assert out_arg.name == "csv"


def test_cli_export_xlsx_calls_xlsx_exporter() -> None:
    with (
        patch.object(run_analytics, "init_schema"),
        patch.object(run_analytics, "init_views"),
        patch.object(run_analytics, "export_all_views_to_xlsx", return_value={}) as mock_xlsx,
    ):
        exit_code = run_analytics.main(["--step", "export-xlsx"])
    assert exit_code == 0
    mock_xlsx.assert_called_once()
    xlsx_path = mock_xlsx.call_args.args[1]
    assert xlsx_path.name == "steam_analytics.xlsx"


def test_cli_all_runs_every_step() -> None:
    with (
        patch.object(run_analytics, "init_schema") as mock_schema,
        patch.object(run_analytics, "init_views") as mock_views,
        patch.object(
            run_analytics, "export_all", return_value={"csv": {}, "xlsx": {}}
        ) as mock_export_all,
    ):
        exit_code = run_analytics.main(["--step", "all"])
    assert exit_code == 0
    mock_schema.assert_called_once()
    mock_views.assert_called_once()
    mock_export_all.assert_called_once()


def test_cli_unknown_step_returns_error() -> None:
    with pytest.raises(SystemExit):
        run_analytics.main(["--step", "bogus"])


def test_cli_out_dir_override_threads_through(tmp_path: Path) -> None:
    custom_dir = tmp_path / "custom_exports"
    with (
        patch.object(run_analytics, "init_schema"),
        patch.object(run_analytics, "init_views"),
        patch.object(run_analytics, "export_all_views_to_csv", return_value={}) as mock_csv,
    ):
        exit_code = run_analytics.main(
            ["--step", "export-csv", "--out-dir", str(custom_dir)]
        )
    assert exit_code == 0
    out_arg = mock_csv.call_args.args[1]
    assert custom_dir in out_arg.parents or out_arg == custom_dir / "csv"
