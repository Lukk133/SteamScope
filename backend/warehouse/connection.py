"""Połączenie z SQLite + inicjalizacja schematu hurtowni.

Wszystkie operacje przyjmują `sqlite3.Connection`. Foreign keys są domyślnie
wyłączone w SQLite — włączamy je przez PRAGMA przy każdym połączeniu.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.config import PATHS

_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
_VIEWS_PATH = Path(__file__).resolve().parent / "views.sql"


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Otwiera połączenie z SQLite i włącza foreign keys.

    ``check_same_thread=False`` — FastAPI może wywołać dependency w innym
    wątku niż sam handler endpointu (asyncio threadpool); połączenie jest
    używane sekwencyjnie w obrębie jednego requestu i zamykane po jego
    zakończeniu, więc to wyłączenie jest bezpieczne.
    """
    db_path = db_path or PATHS.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Wykonuje pełne DDL schematu gwiazdy. Idempotentne (IF NOT EXISTS)."""
    sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()


def init_views(conn: sqlite3.Connection) -> None:
    """Tworzy analityczne widoki warstwy wynikowej.

    Idempotentne — każde wywołanie odtwarza widoki od zera (DROP + CREATE),
    więc bezpiecznie aktualizuje się po zmianie definicji w views.sql.
    """
    sql = _VIEWS_PATH.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()
