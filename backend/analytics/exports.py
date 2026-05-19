"""Eksport widoków analitycznych warstwy wynikowej do CSV i XLSX.

Moduł nie zawiera logiki agregującej — wszystkie obliczenia żyją w `views.sql`.
Eksportery jedynie materializują widoki do plików na dysku.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

VIEW_NAMES: tuple[str, ...] = (
    "vw_top_rated_games",
    "vw_genre_stats",
    "vw_developer_leaderboard",
    "vw_price_range_distribution",
    "vw_sentiment_per_genre",
    "vw_monthly_releases",
)


def _sheet_name(view_name: str) -> str:
    """Zwraca alias arkusza Excel dla nazwy widoku (bez prefiksu ``vw_``)."""
    return view_name.removeprefix("vw_")


def export_view_to_csv(conn: sqlite3.Connection, view_name: str, out_path: Path) -> int:
    """Eksportuje pojedynczy widok do CSV. Zwraca liczbę zapisanych wierszy."""
    if view_name not in VIEW_NAMES:
        raise ValueError(f"Unknown view: {view_name}. Allowed: {VIEW_NAMES}")
    df = pd.read_sql(f"SELECT * FROM {view_name}", conn)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8")
    return len(df)


def export_all_views_to_csv(conn: sqlite3.Connection, out_dir: Path) -> dict[str, int]:
    """Eksportuje wszystkie widoki do osobnych plików CSV w ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for view_name in VIEW_NAMES:
        out_path = out_dir / f"{view_name}.csv"
        counts[view_name] = export_view_to_csv(conn, view_name, out_path)
    return counts


def export_all_views_to_xlsx(conn: sqlite3.Connection, out_path: Path) -> dict[str, int]:
    """Eksportuje wszystkie widoki do jednego pliku XLSX (jeden arkusz per widok)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        for view_name in VIEW_NAMES:
            df = pd.read_sql(f"SELECT * FROM {view_name}", conn)
            sheet = _sheet_name(view_name)
            df.to_excel(writer, sheet_name=sheet, index=False)
            counts[sheet] = len(df)
    return counts


def export_all(conn: sqlite3.Connection, out_dir: Path) -> dict[str, dict[str, int]]:
    """Pełen eksport: CSV-y w ``out_dir/csv`` oraz zbiorczy XLSX w ``out_dir``."""
    csv_counts = export_all_views_to_csv(conn, out_dir / "csv")
    xlsx_counts = export_all_views_to_xlsx(conn, out_dir / "steam_analytics.xlsx")
    return {"csv": csv_counts, "xlsx": xlsx_counts}
