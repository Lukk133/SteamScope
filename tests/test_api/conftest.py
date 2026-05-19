"""Fixtury dla testów API: TestClient z hurtownią z fixture views_conn."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import get_db
from backend.api.main import create_app


def _db_path_of(conn: sqlite3.Connection) -> str:
    """Zwraca ścieżkę pliku SQLite stojącego za otwartym połączeniem."""
    row = conn.execute("PRAGMA database_list").fetchone()
    # Schemat: (seq, name, file). `name` == 'main' jest pierwsze.
    return row[2]


@pytest.fixture
def client(views_conn: sqlite3.Connection) -> Iterator[TestClient]:
    """TestClient z połączeniem ze zbudowaną testową hurtownią.

    TestClient FastAPI uruchamia endpointy w wątku roboczym — SQLite domyślnie
    nie pozwala dzielić połączeń między wątkami. Override otwiera świeże
    połączenie na ten sam plik DB z ``check_same_thread=False`` na czas żądania.
    """
    db_path = _db_path_of(views_conn)
    app = create_app()

    def _override() -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
