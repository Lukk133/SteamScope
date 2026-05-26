"""Endpoint zbiorczy KPI nad widokiem vw_overview.

Widok ``vw_overview`` zawsze zwraca dokładnie jeden wiersz agregatów.
Nazwa widoku jest stałą modułową — brak powierzchni na SQL injection.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.dependencies import DbConn

router = APIRouter(prefix="/api", tags=["overview"])

_VIEW_OVERVIEW = "vw_overview"


@router.get("/overview")
def overview(conn: DbConn) -> dict:
    """Zwraca jeden wiersz KPI dla nagłówka dashboardu."""
    row = conn.execute(f"SELECT * FROM {_VIEW_OVERVIEW}").fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Brak danych overview")
    return dict(row)
