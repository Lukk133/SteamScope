"""Klient SteamSpy API.

Endpoint: https://steamspy.com/api.php?request=appdetails&appid={appid}
Brak uwierzytelniania. Zaleca się <= 1 req/sec, jeden request per appid.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests

from backend.config import INGESTION, PATHS

logger = logging.getLogger(__name__)

STEAMSPY_API_URL = "https://steamspy.com/api.php"


class SteamSpyError(Exception):
    """Błąd komunikacji ze SteamSpy."""


def fetch_app_details(
    appid: int,
    session: requests.Session | None = None,
    timeout: int | None = None,
) -> dict:
    """Pobiera dane o jednej grze. Zwraca surowy JSON (parsing zostaje na ETL)."""
    sess = session or requests.Session()
    sess.headers.update({"User-Agent": INGESTION.user_agent})

    try:
        resp = sess.get(
            STEAMSPY_API_URL,
            params={"request": "appdetails", "appid": appid},
            timeout=timeout or INGESTION.http_timeout_seconds,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.JSONDecodeError as e:
        raise SteamSpyError(f"appid={appid}: invalid JSON – {e}") from e
    except requests.RequestException as e:
        raise SteamSpyError(f"appid={appid}: {e}") from e


def fetch_many(
    appids: list[int],
    target_dir: Path | None = None,
    rate_limit_seconds: float | None = None,
    force: bool = False,
) -> dict[int, str]:
    """Pobiera SteamSpy dla wielu appid. Statusy: 'fetched', 'skipped', 'error'."""
    target_dir = target_dir or PATHS.steamspy_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    delay = (
        rate_limit_seconds
        if rate_limit_seconds is not None
        else INGESTION.steamspy_rate_limit_seconds
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
            data = fetch_app_details(appid, session=session)
        except SteamSpyError as e:
            logger.error("appid=%s error: %s", appid, e)
            statuses[appid] = "error"
            time.sleep(delay)
            continue
        try:
            out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            statuses[appid] = "fetched"
        except OSError as e:
            logger.error("appid=%s write error: %s", appid, e)
            statuses[appid] = "error"
        time.sleep(delay)

    return statuses
