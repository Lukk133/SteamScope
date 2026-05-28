"""Eksport tabel staging do formatu kolumnowego (Parquet) w `data/processed/`.

Parquet (Apache pyarrow) jest formatem kolumnowym — daje ~5–10× mniejsze
pliki niż CSV przy zachowaniu typów. Używamy go jako szybki checkpoint
między uruchomieniami ETL: po wczytaniu surowych plików (CSV/JSON/HTML)
do tabel `stg_*` w SQLite, ich zawartość trafia również do `data/processed/`
jako pliki kolumnowe — kolejne narzędzia analityczne (np. notebook,
PowerBI, Spark) mogą czytać te pliki bezpośrednio bez podłączania się
do hurtowni.
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

STAGING_TABLES: tuple[str, ...] = (
    "stg_kaggle",
    "stg_steam_api",
    "stg_steamspy",
    "stg_reviews",
)


def _coerce_object_columns_to_string(df: pd.DataFrame) -> pd.DataFrame:
    """Zamienia kolumny ``object`` na pandasowy ``string`` dtype.

    pyarrow wymaga jednorodnego typu na kolumnę — staging tables mają
    kolumny mieszane (np. text + None, listy jako stringi CSV), więc bez
    rzutowania Parquet writer rzuca ``ArrowInvalid``.
    """
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype("string")
    return df


def dump_staging_to_parquet(
    conn: sqlite3.Connection, processed_dir: Path
) -> dict[str, int]:
    """Zrzuca wszystkie tabele ``stg_*`` do plików ``.parquet``.

    Args:
        conn: otwarte połączenie SQLite z hurtownią.
        processed_dir: katalog docelowy (zostanie utworzony, jeśli nie istnieje).

    Returns:
        Słownik ``{nazwa_tabeli: liczba_wierszy}``. Tabele nieobecne
        w hurtowni są pomijane (np. gdy etap staging dla danego źródła
        nie był uruchamiany).
    """
    processed_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, int] = {}
    for table in STAGING_TABLES:
        try:
            df = pd.read_sql(f"SELECT * FROM {table}", conn)
        except pd.errors.DatabaseError:
            logger.warning("Pomijam %s — tabela nie istnieje w hurtowni", table)
            continue
        df = _coerce_object_columns_to_string(df)
        out = processed_dir / f"{table}.parquet"
        df.to_parquet(out, engine="pyarrow", index=False)
        written[table] = len(df)
        logger.info("Zapisano %d wierszy do %s", len(df), out)
    return written


def read_staging_parquet(processed_dir: Path, table: str) -> pd.DataFrame:
    """Wczytuje wcześniej zapisaną tabelę staging z pliku Parquet.

    Pozwala omijać re-staging (parsowanie CSV/JSON) w narzędziach, które
    konsumują dane staging po zakończeniu ETL.
    """
    path = processed_dir / f"{table}.parquet"
    return pd.read_parquet(path, engine="pyarrow")
