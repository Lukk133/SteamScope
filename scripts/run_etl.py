"""CLI orkiestrujący warstwę ETL.

Użycie:
    python -m scripts.run_etl --step schema
    python -m scripts.run_etl --step staging
    python -m scripts.run_etl --step dimensions
    python -m scripts.run_etl --step facts
    python -m scripts.run_etl --step all
"""
from __future__ import annotations

import argparse
import logging
import sys

from backend.config import PATHS
from backend.etl.load_dimensions import load_all_dimensions
from backend.etl.load_facts import load_bridges, load_fact_games, load_fact_reviews
from backend.etl.staging import stage_kaggle, stage_reviews, stage_steam_api, stage_steamspy
from backend.warehouse.connection import connect, init_schema

STEPS = ("schema", "staging", "dimensions", "facts", "all")

logger = logging.getLogger("etl")


def _setup_logging() -> None:
    PATHS.ensure()
    log_file = PATHS.logs_dir / "etl.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(log_file)],
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run ETL pipeline for the Steam analytics warehouse.")
    p.add_argument("--step", required=True, choices=STEPS)
    return p


def _run_schema() -> int:
    with connect() as conn:
        init_schema(conn)
    logger.info("Schema initialized at %s", PATHS.db_path)
    return 0


def _run_staging() -> int:
    with connect() as conn:
        init_schema(conn)
        k = stage_kaggle(PATHS.kaggle_dir / "games.csv", conn)
        s = stage_steam_api(PATHS.steam_api_dir, conn)
        sp = stage_steamspy(PATHS.steamspy_dir, conn)
        r = stage_reviews(PATHS.scraped_dir, conn)
    logger.info("Staging done: kaggle=%d steam_api=%d steamspy=%d reviews=%d", k, s, sp, r)
    return 0


def _run_dimensions() -> int:
    with connect() as conn:
        init_schema(conn)
        maps = load_all_dimensions(conn)
    sizes = {k: len(v) for k, v in maps.items()}
    logger.info("Dimensions loaded: %s", sizes)
    return 0


def _run_facts() -> int:
    with connect() as conn:
        init_schema(conn)
        maps = load_all_dimensions(conn)
        games = load_fact_games(conn, maps)
        bridges = load_bridges(conn, maps)
        reviews = load_fact_reviews(conn, maps)
    logger.info("Facts loaded: games=%d reviews=%d bridges=%s", games, reviews, bridges)
    return 0


def _run_all() -> int:
    with connect() as conn:
        init_schema(conn)
        k = stage_kaggle(PATHS.kaggle_dir / "games.csv", conn)
        s = stage_steam_api(PATHS.steam_api_dir, conn)
        sp = stage_steamspy(PATHS.steamspy_dir, conn)
        r = stage_reviews(PATHS.scraped_dir, conn)
        logger.info("Staging: kaggle=%d steam_api=%d steamspy=%d reviews=%d", k, s, sp, r)
        maps = load_all_dimensions(conn)
        logger.info("Dimensions: %s", {k: len(v) for k, v in maps.items()})
        games = load_fact_games(conn, maps)
        bridges = load_bridges(conn, maps)
        reviews = load_fact_reviews(conn, maps)
        logger.info("Facts: games=%d reviews=%d bridges=%s", games, reviews, bridges)
    return 0


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    args = _build_parser().parse_args(argv)
    dispatch = {
        "schema": _run_schema,
        "staging": _run_staging,
        "dimensions": _run_dimensions,
        "facts": _run_facts,
        "all": _run_all,
    }
    return dispatch[args.step]()


if __name__ == "__main__":
    raise SystemExit(main())
