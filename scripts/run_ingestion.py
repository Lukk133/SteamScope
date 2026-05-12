"""CLI orkiestrujący warstwę ingestion.

Użycie:
    python -m scripts.run_ingestion --source kaggle
    python -m scripts.run_ingestion --source steam --appids 70,220,440
    python -m scripts.run_ingestion --source all --appids 70,220 --force
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from backend.config import PATHS
from backend.ingestion.fetch_steam_api import fetch_many as fetch_steam_api_many
from backend.ingestion.fetch_steamspy import fetch_many as fetch_steamspy_many
from backend.ingestion.load_kaggle import download_kaggle_dataset
from backend.ingestion.scrape_reviews import scrape_many as scrape_reviews_many

SOURCES = ("kaggle", "steam", "steamspy", "reviews", "all")

logger = logging.getLogger("ingestion")


def _setup_logging() -> None:
    PATHS.ensure()
    log_file = PATHS.logs_dir / "ingestion.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(log_file)],
    )


def _parse_appids(text: str) -> list[int]:
    text = text.strip()
    if not text:
        return []
    return [int(tok.strip()) for tok in text.split(",") if tok.strip()]


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run ingestion for the Steam analytics project.")
    p.add_argument("--source", required=True, choices=SOURCES)
    p.add_argument(
        "--appids",
        default="",
        help="Comma-separated list of Steam appids (required for steam/steamspy/reviews/all).",
    )
    p.add_argument("--force", action="store_true", help="Ignore cached files and refetch.")
    return p


def _run_kaggle(force: bool) -> int:
    path = download_kaggle_dataset(force=force)
    logger.info("Kaggle dataset at %s", path)
    return 0


def _run_steam(appids: list[int], force: bool) -> int:
    statuses = fetch_steam_api_many(appids=appids, force=force)
    logger.info("Steam API statuses: %s", statuses)
    return 0


def _run_steamspy(appids: list[int], force: bool) -> int:
    statuses = fetch_steamspy_many(appids=appids, force=force)
    logger.info("SteamSpy statuses: %s", statuses)
    return 0


def _run_reviews(appids: list[int], force: bool) -> int:
    statuses = scrape_reviews_many(appids=appids, force=force)
    logger.info("Reviews statuses: %s", statuses)
    return 0


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    args = _build_parser().parse_args(argv)
    appids = _parse_appids(args.appids)

    needs_appids = args.source in {"steam", "steamspy", "reviews", "all"}
    if needs_appids and not appids:
        logger.error("--appids is required for source=%s", args.source)
        return 2

    if args.source == "kaggle":
        return _run_kaggle(force=args.force)
    if args.source == "steam":
        return _run_steam(appids, force=args.force)
    if args.source == "steamspy":
        return _run_steamspy(appids, force=args.force)
    if args.source == "reviews":
        return _run_reviews(appids, force=args.force)
    if args.source == "all":
        rc = _run_kaggle(force=args.force)
        if rc != 0:
            return rc
        for fn in (_run_steam, _run_steamspy, _run_reviews):
            rc = fn(appids, force=args.force)
            if rc != 0:
                return rc
        return 0
    return 2  # unreachable due to argparse choices


if __name__ == "__main__":
    raise SystemExit(main())
