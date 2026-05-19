"""Testy eksporterów widoków analitycznych do CSV/XLSX."""
from __future__ import annotations

import pandas as pd
import pytest

from backend.analytics.exports import (
    VIEW_NAMES,
    export_all,
    export_all_views_to_csv,
    export_all_views_to_xlsx,
    export_view_to_csv,
)

_EXPECTED_SHEETS = (
    "top_rated_games",
    "genre_stats",
    "developer_leaderboard",
    "price_range_distribution",
    "sentiment_per_genre",
    "monthly_releases",
)


def test_export_view_to_csv_writes_rows(views_conn, tmp_path) -> None:
    out_path = tmp_path / "vw_genre_stats.csv"
    rows = export_view_to_csv(views_conn, "vw_genre_stats", out_path)
    assert out_path.exists()
    df = pd.read_csv(out_path)
    assert len(df) == rows
    expected = pd.read_sql("SELECT * FROM vw_genre_stats", views_conn)
    assert list(df.columns) == list(expected.columns)


def test_export_view_to_csv_rejects_unknown_name(views_conn, tmp_path) -> None:
    with pytest.raises(ValueError, match="vw_does_not_exist"):
        export_view_to_csv(views_conn, "vw_does_not_exist", tmp_path / "x.csv")


def test_export_view_to_csv_creates_parent_dir(views_conn, tmp_path) -> None:
    nested = tmp_path / "deep" / "dir" / "x.csv"
    assert not nested.parent.exists()
    export_view_to_csv(views_conn, "vw_genre_stats", nested)
    assert nested.parent.is_dir()
    assert nested.exists()


def test_export_all_views_to_csv_creates_six_files(views_conn, tmp_path) -> None:
    out_dir = tmp_path / "csv_out"
    counts = export_all_views_to_csv(views_conn, out_dir)
    assert set(counts.keys()) == set(VIEW_NAMES)
    assert len(counts) == 6
    for view_name in VIEW_NAMES:
        assert (out_dir / f"{view_name}.csv").exists()


def test_export_all_views_to_xlsx_creates_six_sheets(views_conn, tmp_path) -> None:
    out_path = tmp_path / "steam_analytics.xlsx"
    counts = export_all_views_to_xlsx(views_conn, out_path)
    assert out_path.exists()
    assert set(counts.keys()) == set(_EXPECTED_SHEETS)
    # Excel limit 31 znaków.
    assert all(len(name) <= 31 for name in counts.keys())
    xl = pd.ExcelFile(out_path)
    assert set(xl.sheet_names) == set(_EXPECTED_SHEETS)
    assert len(xl.sheet_names) == 6


def test_export_all_views_to_xlsx_sheet_content_matches_view(views_conn, tmp_path) -> None:
    out_path = tmp_path / "steam_analytics.xlsx"
    export_all_views_to_xlsx(views_conn, out_path)
    from_excel = pd.read_excel(out_path, sheet_name="genre_stats")
    from_sql = pd.read_sql("SELECT * FROM vw_genre_stats", views_conn)
    pd.testing.assert_frame_equal(
        from_excel.reset_index(drop=True),
        from_sql.reset_index(drop=True),
        check_dtype=False,
    )


def test_export_all_calls_both_layers(views_conn, tmp_path) -> None:
    out_dir = tmp_path / "exports"
    result = export_all(views_conn, out_dir)
    assert set(result.keys()) == {"csv", "xlsx"}
    assert len(result["csv"]) == 6
    assert len(result["xlsx"]) == 6
    # Fizyczne artefakty istnieją.
    assert (out_dir / "steam_analytics.xlsx").exists()
    for view_name in VIEW_NAMES:
        assert (out_dir / "csv" / f"{view_name}.csv").exists()
