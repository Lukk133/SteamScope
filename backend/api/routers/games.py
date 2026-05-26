"""Endpointy listy/wyszukiwania gier i szczegółów pojedynczej gry.

Zapytania idą po stałym widoku ``vw_game_detail``; ``q`` i ``game_id``
trafiają wyłącznie jako parametry — brak powierzchni na SQL injection.
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException, Query

from backend.api.dependencies import DbConn

router = APIRouter(prefix="/api/games", tags=["games"])

_VIEW_GAME_DETAIL = "vw_game_detail"


@router.get("")
def list_games(
    conn: DbConn,
    q: str | None = Query(None, description="Filtr po nazwie (LIKE, bez rozróżniania wielkości)."),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """Lista gier z opcjonalnym filtrem nazwy i paginacją.

    Zwraca ``{"items": [...], "total": <int>}`` — ``total`` po filtrze,
    przed paginacją.
    """
    where_sql = ""
    where_params: list[str] = []
    if q:
        where_sql = " WHERE name LIKE ?"
        where_params.append(f"%{q}%")

    rows = conn.execute(
        f"SELECT * FROM {_VIEW_GAME_DETAIL}{where_sql} "
        "ORDER BY rating_score DESC, review_count DESC LIMIT ? OFFSET ?",
        (*where_params, limit, offset),
    ).fetchall()
    total_row = conn.execute(
        f"SELECT COUNT(*) AS c FROM {_VIEW_GAME_DETAIL}{where_sql}",
        where_params,
    ).fetchone()
    return {"items": [dict(r) for r in rows], "total": int(total_row["c"])}


@router.get("/{game_id}")
def game_detail(conn: DbConn, game_id: int) -> dict:
    """Pełny rekord pojedynczej gry albo 404, gdy brak."""
    row: sqlite3.Row | None = conn.execute(
        f"SELECT * FROM {_VIEW_GAME_DETAIL} WHERE game_id = ?",
        (game_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono gry")
    return dict(row)
