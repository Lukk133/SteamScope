"""Czyste funkcje pomocnicze używane w warstwie ETL.

Każda funkcja jest deterministyczna, nie ma efektów ubocznych i jest
testowalna w izolacji.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any

_PRICE_BUCKETS: list[tuple[float, float | None, str]] = [
    (0.01, 4.99, "$0.01-4.99"),
    (5.00, 14.99, "$5-14.99"),
    (15.00, 29.99, "$15-29.99"),
    (30.00, 59.99, "$30-59.99"),
    (60.00, None, "$60+"),
]

_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

_SEASONS_BY_MONTH = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring", 4: "Spring", 5: "Spring",
    6: "Summer", 7: "Summer", 8: "Summer",
    9: "Autumn", 10: "Autumn", 11: "Autumn",
}

_DATE_FORMATS = ["%Y-%m-%d", "%b %d, %Y", "%d %b, %Y", "%B %d, %Y"]


def parse_owners_range(raw: Any) -> int | None:
    """Konwertuje 'A .. B' (z przecinkami) na liczbę całkowitą (midpoint).

    Zwraca None przy braku/błędzie.
    """
    if raw is None or not isinstance(raw, str):
        return None
    parts = raw.split("..")
    if len(parts) != 2:
        return None
    try:
        lo = int(parts[0].strip().replace(",", ""))
        hi = int(parts[1].strip().replace(",", ""))
    except (ValueError, AttributeError):
        return None
    return (lo + hi) // 2


def price_to_range_label(price: float | None) -> str:
    """Mapuje cenę USD na etykietę przedziału cenowego."""
    if price is None or (isinstance(price, float) and math.isnan(price)) or price <= 0:
        return "Free"
    for lo, hi, label in _PRICE_BUCKETS:
        if hi is None and price >= lo:
            return label
        if hi is not None and lo <= price <= hi:
            return label
    return "Free"


def classify_developer(games_count: int) -> str:
    """Klasyfikuje dewelopera na podstawie liczby wydanych gier.

    1-2 → indie, 3-10 → AA, 11+ → AAA. Liczba musi być >=1.
    """
    if games_count < 1:
        raise ValueError(f"games_count must be >=1, got {games_count}")
    if games_count <= 2:
        return "indie"
    if games_count <= 10:
        return "AA"
    return "AAA"


def release_date_to_period(raw: Any) -> dict | None:
    """Parsuje datę premiery i zwraca słownik z year/quarter/month/month_name/season.

    Obsługuje formaty: ISO (2024-03-15), Steam ('Nov 8, 1998', '8 Nov, 1998'),
    pełne ('November 8, 1998'). Zwraca None przy nieparsowalnym wejściu.
    """
    if raw is None or not isinstance(raw, str) or not raw.strip():
        return None
    dt: datetime | None = None
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(raw.strip(), fmt)
            break
        except ValueError:
            continue
    if dt is None:
        return None
    return {
        "year": dt.year,
        "quarter": (dt.month - 1) // 3 + 1,
        "month": dt.month,
        "month_name": _MONTH_NAMES[dt.month - 1],
        "season": _SEASONS_BY_MONTH[dt.month],
    }
