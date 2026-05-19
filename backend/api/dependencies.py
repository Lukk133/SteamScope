"""Zależności FastAPI: dostęp do hurtowni SQLite."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends

from backend.warehouse.connection import connect


def get_db() -> Iterator[sqlite3.Connection]:
    """Otwiera połączenie do hurtowni i zamyka po zakończeniu zapytania."""
    conn = connect()
    conn.row_factory = sqlite3.Row  # so rows look like dicts
    try:
        yield conn
    finally:
        conn.close()


DbConn = Annotated[sqlite3.Connection, Depends(get_db)]
