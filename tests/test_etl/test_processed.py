"""Testy zrzutu staging tables do plików Parquet (data/processed/)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from backend.etl.processed import (
    STAGING_TABLES,
    dump_staging_to_parquet,
    read_staging_parquet,
)


def test_dump_creates_parquet_for_each_staging_table(
    views_conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """Każda obecna tabela stg_* trafia do pliku parquet o tej samej nazwie."""
    out_dir = tmp_path / "processed"
    written = dump_staging_to_parquet(views_conn, out_dir)

    # Fixture views_conn zawsze ładuje wszystkie 4 staging tables.
    for table in STAGING_TABLES:
        assert table in written, f"Brak {table} w wyniku dump_staging_to_parquet"
        path = out_dir / f"{table}.parquet"
        assert path.exists(), f"Plik {path} nie został utworzony"


def test_dump_roundtrip_preserves_row_counts(
    views_conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """Liczba wierszy w parquet zgadza się z liczbą w tabeli źródłowej."""
    out_dir = tmp_path / "processed"
    dump_staging_to_parquet(views_conn, out_dir)

    for table in STAGING_TABLES:
        expected = int(views_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        df = read_staging_parquet(out_dir, table)
        assert len(df) == expected, f"Rozjazd liczby wierszy dla {table}"


def test_dump_skips_missing_tables(tmp_path: Path) -> None:
    """Tabele nieobecne w pustej hurtowni są pomijane bez błędu."""
    empty_db = tmp_path / "empty.db"
    conn = sqlite3.connect(empty_db)
    try:
        written = dump_staging_to_parquet(conn, tmp_path / "processed")
    finally:
        conn.close()

    assert written == {}, "Pusta hurtownia nie powinna nic zapisać"


def test_read_parquet_missing_file_raises(tmp_path: Path) -> None:
    """Próba odczytu nieistniejącego parqueta rzuca przewidywalny błąd."""
    with pytest.raises(FileNotFoundError):
        read_staging_parquet(tmp_path, "stg_kaggle")


def test_dump_handles_object_columns_with_nulls(
    views_conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """Object columns z NULL-ami (typowe dla stg_kaggle) trafiają poprawnie do parquet.

    pyarrow domyślnie wybucha na kolumnach object z mieszanymi typami;
    moduł powinien rzutować je na pandasowy string dtype przed zapisem.
    """
    out_dir = tmp_path / "processed"
    dump_staging_to_parquet(views_conn, out_dir)

    df = read_staging_parquet(out_dir, "stg_kaggle")
    # Sanity: jest kolumna name, typ string, są jakieś wartości i jakieś NULL-e
    # nie spowodowały błędu zapisu.
    assert "name" in df.columns
    assert pd.api.types.is_string_dtype(df["name"])
