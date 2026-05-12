"""Klient Steam Store Web API.

Endpoint nie wymaga uwierzytelnienia, ale ma agresywne rate limity (~200/5min);
batchowanie obsługujemy w funkcji `fetch_many` (Task 5).
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests

from backend.config import INGESTION, PATHS

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
        payload = resp.json()
    except requests.exceptions.JSONDecodeError as e:
        raise SteamAPIError(f"appid={appid}: invalid JSON – {e}") from e
    except requests.RequestException as e:
        raise SteamAPIError(f"appid={appid}: {e}") from e
    entry = payload.get(str(appid), {})
    if not entry.get("success"):
        logger.warning("Steam API success=false for appid %s", appid)
        return None
    return entry.get("data")


def fetch_many(
    appids: list[int],
    target_dir: Path | None = None,
    rate_limit_seconds: float | None = None,
    force: bool = False,
) -> dict[int, str]:
    """Pobiera szczegóły wielu gier. Każdy wynik zapisany jako `{appid}.json`.

    Statusy zwracane: "fetched", "missing", "skipped", "error".
    Rate-limited i idempotentne. Domyślnie `target_dir = PATHS.steam_api_dir`.
    """
    target_dir = target_dir or PATHS.steam_api_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    delay = (
        rate_limit_seconds
        if rate_limit_seconds is not None
        else INGESTION.steam_api_rate_limit_seconds
    )

    session = requests.Session()
    session.headers.update({"User-Agent": INGESTION.user_agent})
    statuses: dict[int, str] = {}

    for appid in appids:
        out = target_dir / f"{appid}.json"
        if out.exists() and not force:
            statuses[appid] = "skipped"
            continue
        try:
            data = fetch_game_details(appid, session=session)
        except SteamAPIError as e:
            logger.error("appid=%s error: %s", appid, e)
            statuses[appid] = "error"
            time.sleep(delay)
            continue

        try:
            if data is None:
                out.write_text(json.dumps({"_missing": True}), encoding="utf-8")
                statuses[appid] = "missing"
            else:
                out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                statuses[appid] = "fetched"
        except OSError as e:
            logger.error("appid=%s write error: %s", appid, e)
            statuses[appid] = "error"
        time.sleep(delay)

    return statuses
