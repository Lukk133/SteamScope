"""CLI orkiestrujący warstwę analityczną.

Użycie:
    python -m scripts.run_analytics --step views
    python -m scripts.run_analytics --step export-csv
    python -m scripts.run_analytics --step export-xlsx
    python -m scripts.run_analytics --step all

Opcjonalnie ``--out-dir <path>`` nadpisuje domyślny katalog eksportu
(``PATHS.exports_dir``).
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from backend.analytics.exports import (
    export_all,
    export_all_views_to_csv,
    export_all_views_to_xlsx,
)
from backend.config import PATHS
from backend.warehouse.connection import connect, init_schema, init_views

STEPS = ("views", "export-csv", "export-xlsx", "all")

logger = logging.getLogger("analytics")


def _setup_logging() -> None:
    PATHS.ensure()
    log_file = PATHS.logs_dir / "analytics.log"
    # Wymuś UTF-8 na stdout (Windows domyślnie cp1250) — patrz komentarz
    # w scripts/run_etl.py._setup_logging.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run analytics layer for the Steam analytics warehouse."
    )
    p.add_argument("--step", required=True, choices=STEPS)
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Katalog wyjściowy dla eksportów (domyślnie PATHS.exports_dir).",
    )
    return p


def _resolve_out_dir(out_dir: Path | None) -> Path:
    """Zwraca docelowy katalog eksportu — z flagi lub domyślny z konfiguracji."""
    return out_dir if out_dir is not None else PATHS.exports_dir


def _run_views() -> int:
    with connect() as conn:
        init_schema(conn)
        init_views(conn)
        cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view'")
        view_count = cursor.fetchone()[0]
    logger.info("Views initialized: %d views in database", view_count)
    return 0


def _run_export_csv(out_dir: Path) -> int:
    with connect() as conn:
        init_schema(conn)
        init_views(conn)
        counts = export_all_views_to_csv(conn, out_dir / "csv")
    logger.info("CSV exports written to %s: %s", out_dir / "csv", counts)
    return 0


def _run_export_xlsx(out_dir: Path) -> int:
    xlsx_path = out_dir / "steam_analytics.xlsx"
    with connect() as conn:
        init_schema(conn)
        init_views(conn)
        counts = export_all_views_to_xlsx(conn, xlsx_path)
    logger.info("XLSX export written to %s: %s", xlsx_path, counts)
    return 0


def _run_all(out_dir: Path) -> int:
    with connect() as conn:
        init_schema(conn)
        init_views(conn)
        result = export_all(conn, out_dir)
    logger.info("Full analytics export to %s: %s", out_dir, result)
    return 0


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    args = _build_parser().parse_args(argv)
    out_dir = _resolve_out_dir(args.out_dir)
    dispatch = {
        "views": lambda: _run_views(),
        "export-csv": lambda: _run_export_csv(out_dir),
        "export-xlsx": lambda: _run_export_xlsx(out_dir),
        "all": lambda: _run_all(out_dir),
    }
    return dispatch[args.step]()


if __name__ == "__main__":
    raise SystemExit(main())
