"""Połączenie z SQLite + inicjalizacja schematu hurtowni.

Wszystkie operacje przyjmują `sqlite3.Connection`. Foreign keys są domyślnie
wyłączone w SQLite — włączamy je przez PRAGMA przy każdym połączeniu.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3

from backend.config import PATHS

_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Otwiera połączenie z SQLite i włącza foreign keys."""
    db_path = db_path or PATHS.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Wykonuje pełne DDL schematu gwiazdy. Idempotentne (IF NOT EXISTS)."""
    sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()
