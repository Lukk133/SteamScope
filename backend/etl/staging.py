"""Staging — raw pliki → stg_* tabele w SQLite.

Każda funkcja:
- czyta z katalogu/pliku w `data/raw/`
- normalizuje typy (int, float, bool jako 0/1, listy jako CSV-stringi)
- zapisuje do tabeli `stg_*` przez `df.to_sql(..., if_exists='replace')`
- zwraca liczbę zapisanych wierszy
"""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

import pandas as pd

from backend.etl.parsers import parse_owners_range

logger = logging.getLogger(__name__)


def _truthy_to_int(series: pd.Series) -> pd.Series:
    return series.fillna(False).astype(bool).astype(int)


def stage_kaggle(csv_path: Path, conn: sqlite3.Connection) -> int:
    """Ładuje Kaggle CSV do `stg_kaggle`. Zwraca liczbę wierszy."""
    if not csv_path.exists():
        logger.warning("Kaggle CSV not found at %s — staging 0 rows", csv_path)
        pd.DataFrame().to_sql("stg_kaggle", conn, if_exists="replace", index=False)
        return 0

    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    if "appid" in df.columns:
        df["appid"] = pd.to_numeric(df["appid"], errors="coerce").astype("Int64")
        df = df.dropna(subset=["appid"])
        df["appid"] = df["appid"].astype(int)

    for col in ("windows", "mac", "linux"):
        if col in df.columns:
            df[col] = _truthy_to_int(df[col])

    if "price" in df.columns:
        df["price"] = pd.to_numeric(df["price"], errors="coerce")

    df.to_sql("stg_kaggle", conn, if_exists="replace", index=False)
    conn.commit()
    return len(df)


def stage_steam_api(source_dir: Path, conn: sqlite3.Connection) -> int:
    """Ładuje wszystkie `data/raw/steam_api/{appid}.json` do `stg_steam_api`.

    Pomija pliki z `_missing: true`.
    """
    rows: list[dict] = []
    if source_dir.exists():
        for path in sorted(source_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed JSON: %s", path)
                continue
            if data.get("_missing"):
                continue
            rows.append({
                "appid": int(data.get("steam_appid") or path.stem),
                "name": data.get("name"),
                "is_free": int(bool(data.get("is_free"))),
                "developers": ",".join(data.get("developers", []) or []),
                "publishers": ",".join(data.get("publishers", []) or []),
                "price_usd": (
                    (data.get("price_overview") or {}).get("final", 0) / 100
                    if data.get("price_overview")
                    else 0.0
                ),
                "windows": int(bool((data.get("platforms") or {}).get("windows"))),
                "mac": int(bool((data.get("platforms") or {}).get("mac"))),
                "linux": int(bool((data.get("platforms") or {}).get("linux"))),
                "categories": ",".join(
                    c.get("description", "") for c in (data.get("categories") or [])
                ),
                "genres": ",".join(
                    g.get("description", "") for g in (data.get("genres") or [])
                ),
                "release_date": (data.get("release_date") or {}).get("date"),
            })
    df = pd.DataFrame(rows)
    df.to_sql("stg_steam_api", conn, if_exists="replace", index=False)
    conn.commit()
    return len(df)


def stage_steamspy(source_dir: Path, conn: sqlite3.Connection) -> int:
    """Ładuje wszystkie `data/raw/steamspy/{appid}.json` do `stg_steamspy`.

    Konwertuje `owners` (string range) na midpoint w `estimated_owners`.
    """
    rows: list[dict] = []
    if source_dir.exists():
        for path in sorted(source_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed JSON: %s", path)
                continue
            owners_mid = parse_owners_range(data.get("owners"))
            rows.append({
                "appid": int(data.get("appid") or path.stem),
                "name": data.get("name"),
                "developer": data.get("developer"),
                "estimated_owners": owners_mid,
                "average_forever_minutes": data.get("average_forever"),
                "price_cents": (
                    int(data["price"]) if str(data.get("price") or "").isdigit() else None
                ),
                "positive": data.get("positive"),
                "negative": data.get("negative"),
            })
    df = pd.DataFrame(rows)
    df.to_sql("stg_steamspy", conn, if_exists="replace", index=False)
    conn.commit()
    return len(df)


def stage_reviews(source_dir: Path, conn: sqlite3.Connection) -> int:
    """Ładuje recenzje z `data/raw/scraped/{appid}_reviews.json` do `stg_reviews`."""
    rows: list[dict] = []
    if source_dir.exists():
        for path in sorted(source_dir.glob("*_reviews.json")):
            try:
                reviews = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed JSON: %s", path)
                continue
            for r in reviews or []:
                rows.append({
                    "appid": int(r.get("appid")),
                    "author": r.get("author"),
                    "voted_up": int(bool(r.get("voted_up"))),
                    "playtime_hours": r.get("playtime_hours"),
                    "review_text": r.get("review_text") or "",
                    "posted_date": r.get("posted_date"),
                    "helpful_count": r.get("helpful_count"),
                })
    if rows:
        df = pd.DataFrame(rows)
    else:
        df = pd.DataFrame(columns=[
            "appid", "author", "voted_up", "playtime_hours",
            "review_text", "posted_date", "helpful_count",
        ])
    df.to_sql("stg_reviews", conn, if_exists="replace", index=False)
    conn.commit()
    return len(df)
