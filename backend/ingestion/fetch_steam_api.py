"""Klient Steam Store Web API.

Endpoint nie wymaga uwierzytelnienia, ale ma agresywne rate limity (~200/5min);
batchowanie obsługujemy w funkcji `fetch_many` (Task 5).
"""
from __future__ import annotations

import logging

import requests

from backend.config import INGESTION

logger = logging.getLogger(__name__)

STEAM_API_URL = "https://store.steampowered.com/api/appdetails"


class SteamAPIError(Exception):
    """Błąd komunikacji z Steam Web API."""


def fetch_game_details(
    appid: int,
    session: requests.Session | None = None,
    timeout: int | None = None,
) -> dict | None:
    """Pobiera szczegóły jednej gry. Zwraca dict z `data` lub None gdy gra niedostępna.

    Wyjątek `SteamAPIError` przy błędach sieci/HTTP.
    """
    sess = session or requests.Session()
    sess.headers.update({"User-Agent": INGESTION.user_agent})

    try:
        resp = sess.get(
            STEAM_API_URL,
            params={"appids": appid, "cc": "us", "l": "en"},
            timeout=timeout or INGESTION.http_timeout_seconds,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise SteamAPIError(f"appid={appid}: {e}") from e

    payload = resp.json()
    entry = payload.get(str(appid), {})
    if not entry.get("success"):
        logger.warning("Steam API success=false for appid %s", appid)
        return None
    return entry.get("data")
