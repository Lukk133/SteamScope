"""Endpointy REST nad widokami analitycznymi hurtowni.

Każdy endpoint zwraca słownik ``{"items": [...], "total": <int>}``:

* ``items`` — wiersze widoku zserializowane jako listy słowników,
* ``total`` — liczba wierszy widoku (po ewentualnym filtrze, przed paginacją).

Nazwy widoków są stałymi modułowymi — nigdy nie pochodzą z danych wejściowych
użytkownika, dzięki czemu nie ma powierzchni na SQL injection.
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Query

from backend.api.dependencies import DbConn

router = APIRouter(prefix="/api/views", tags=["views"])

# Mapowanie endpoint → nazwa widoku w hurtowni. Wszystkie wartości są stałymi.
_VIEW_TOP_RATED_GAMES = "vw_top_rated_games"
_VIEW_GENRE_STATS = "vw_genre_stats"
_VIEW_DEVELOPER_LEADERBOARD = "vw_developer_leaderboard"
_VIEW_PRICE_RANGE_DISTRIBUTION = "vw_price_range_distribution"
_VIEW_SENTIMENT_PER_GENRE = "vw_sentiment_per_genre"
_VIEW_MONTHLY_RELEASES = "vw_monthly_releases"


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    """Konwertuje listę ``sqlite3.Row`` na listę słowników JSON-serializowalnych."""
    return [dict(r) for r in rows]


def _count(conn: sqlite3.Connection, view: str) -> int:
    """Zwraca liczbę wierszy w widoku (pełną, bez filtrów)."""
    row = conn.execute(f"SELECT COUNT(*) AS c FROM {view}").fetchone()
    return int(row["c"])


@router.get("/top-rated-games")
def top_rated_games(
    conn: DbConn,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """Ranking najwyżej ocenianych gier (próg ≥ 10 recenzji) z paginacją."""
    rows = conn.execute(
        f"SELECT * FROM {_VIEW_TOP_RATED_GAMES} LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    return {"items": _rows_to_dicts(rows), "total": _count(conn, _VIEW_TOP_RATED_GAMES)}


@router.get("/genre-stats")
def genre_stats(conn: DbConn) -> dict:
    """Zagregowane statystyki per gatunek — pełna lista (zbiór niewielki)."""
    rows = conn.execute(f"SELECT * FROM {_VIEW_GENRE_STATS}").fetchall()
    return {"items": _rows_to_dicts(rows), "total": len(rows)}


@router.get("/developer-leaderboard")
def developer_leaderboard(
    conn: DbConn,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """Liderzy wśród deweloperów po szacowanym przychodzie — z paginacją."""
    rows = conn.execute(
        f"SELECT * FROM {_VIEW_DEVELOPER_LEADERBOARD} LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    return {
        "items": _rows_to_dicts(rows),
        "total": _count(conn, _VIEW_DEVELOPER_LEADERBOARD),
    }


@router.get("/price-range-distribution")
def price_range_distribution(conn: DbConn) -> dict:
    """Rozkład liczby gier w przedziałach cenowych — pełna lista."""
    rows = conn.execute(f"SELECT * FROM {_VIEW_PRICE_RANGE_DISTRIBUTION}").fetchall()
    return {"items": _rows_to_dicts(rows), "total": len(rows)}


@router.get("/sentiment-per-genre")
def sentiment_per_genre(conn: DbConn) -> dict:
    """Rozkład sentymentu recenzji per gatunek — pełna lista."""
    rows = conn.execute(f"SELECT * FROM {_VIEW_SENTIMENT_PER_GENRE}").fetchall()
    return {"items": _rows_to_dicts(rows), "total": len(rows)}


@router.get("/monthly-releases")
def monthly_releases(
    conn: DbConn,
    year_from: int | None = Query(None),
    year_to: int | None = Query(None),
) -> dict:
    """Liczba premier per rok/miesiąc z opcjonalnym filtrem zakresu lat (włącznie)."""
    clauses: list[str] = []
    params: list[int] = []
    if year_from is not None:
        clauses.append("year >= ?")
        params.append(year_from)
    if year_to is not None:
        clauses.append("year <= ?")
        params.append(year_to)
    where_sql = f" WHERE {' AND '.join(clauses)}" if clauses else ""

    rows = conn.execute(
        f"SELECT * FROM {_VIEW_MONTHLY_RELEASES}{where_sql}",
        params,
    ).fetchall()
    total_row = conn.execute(
        f"SELECT COUNT(*) AS c FROM {_VIEW_MONTHLY_RELEASES}{where_sql}",
        params,
    ).fetchone()
    return {"items": _rows_to_dicts(rows), "total": int(total_row["c"])}
